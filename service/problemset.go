package service

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"cfProblemList/models"
)

const (
	dataDir         = "./data/problemsets"
	indexFile       = "./data/problemsets/index.json"
	cacheExpiration = 5 * time.Minute
)

// CacheItem 缓存项
type CacheItem struct {
	Data      interface{}
	ExpiresAt time.Time
}

// ProblemSetService 题单服务
type ProblemSetService struct {
	cache     map[string]CacheItem
	cacheLock sync.RWMutex
}

// NewProblemSetService 创建新的题单服务
func NewProblemSetService() *ProblemSetService {
	return &ProblemSetService{
		cache: make(map[string]CacheItem),
	}
}

// getFromCache 从缓存获取数据
func (s *ProblemSetService) getFromCache(key string) (interface{}, bool) {
	s.cacheLock.RLock()
	defer s.cacheLock.RUnlock()

	item, exists := s.cache[key]
	if !exists || time.Now().After(item.ExpiresAt) {
		return nil, false
	}
	return item.Data, true
}

// setCache 设置缓存
func (s *ProblemSetService) setCache(key string, data interface{}) {
	s.cacheLock.Lock()
	defer s.cacheLock.Unlock()

	s.cache[key] = CacheItem{
		Data:      data,
		ExpiresAt: time.Now().Add(cacheExpiration),
	}
}

// IndexItem index.json 中的条目
type IndexItem struct {
	ID          string `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Category    string `json:"category"`
}

// GetProblemSetList 获取题单列表
// 从 index.json 读取题单封面信息，从各题单文件读取 sections
func (s *ProblemSetService) GetProblemSetList() ([]models.ProblemSetSummary, error) {
	// 尝试从缓存获取
	if data, ok := s.getFromCache("list"); ok {
		return data.([]models.ProblemSetSummary), nil
	}

	// 读取 index.json 获取封面信息
	var indexItems []IndexItem
	indexData, err := os.ReadFile(indexFile)
	if err == nil {
		json.Unmarshal(indexData, &indexItems)
	}
	// 建立 id -> indexItem 映射
	indexMap := make(map[string]IndexItem)
	for _, item := range indexItems {
		indexMap[item.ID] = item
	}

	var summaries []models.ProblemSetSummary

	// 扫描题单目录，从各个文件中提取 sections
	files, err := os.ReadDir(dataDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read data directory: %w", err)
	}

	for _, file := range files {
		if file.IsDir() || filepath.Ext(file.Name()) != ".json" {
			continue
		}

		// 跳过 index.json
		if file.Name() == "index.json" {
			continue
		}

		fileID := file.Name()[:len(file.Name())-5] // 去掉 ".json"
		filePath := filepath.Join(dataDir, file.Name())
		data, err := os.ReadFile(filePath)
		if err != nil {
			continue
		}

		var ps models.ProblemSet
		if err := json.Unmarshal(data, &ps); err != nil {
			continue
		}

		// 提取章节简要信息
		var sections []models.SectionSummary
		for _, section := range ps.Sections {
			sectionSummary := models.SectionSummary{
				Title: section.Title,
			}
			// 优先使用 section.Text 作为描述
			if section.Text != "" {
				sectionSummary.Description = section.Text
			} else {
				// 否则从 content 中提取第一个 paragraph 作为描述
				for _, content := range section.Content {
					if content.Type == "paragraph" && content.Text != "" {
						sectionSummary.Description = content.Text
						break
					}
				}
			}
			sections = append(sections, sectionSummary)
		}

		// 优先使用 index.json 中的封面信息
		title := ps.Title
		description := ps.Description
		category := ps.Category
		if indexItem, ok := indexMap[fileID]; ok {
			title = indexItem.Title
			description = indexItem.Description
			category = indexItem.Category
		}

		summaries = append(summaries, models.ProblemSetSummary{
			ID:          fileID,
			Title:       title,
			Description: description,
			Category:    category,
			Sections:    sections,
		})
	}

	s.setCache("list", summaries)
	return summaries, nil
}

// GetProblemSetByID 根据 ID 获取题单详情
func (s *ProblemSetService) GetProblemSetByID(id string) (*models.ProblemSet, error) {
	cacheKey := "problemset:" + id

	// 尝试从缓存获取
	if data, ok := s.getFromCache(cacheKey); ok {
		return data.(*models.ProblemSet), nil
	}

	// 读取文件
	filePath := filepath.Join(dataDir, id+".json")
	data, err := os.ReadFile(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("problemset not found: %s", id)
		}
		return nil, fmt.Errorf("failed to read problemset file: %w", err)
	}

	var ps models.ProblemSet
	if err := json.Unmarshal(data, &ps); err != nil {
		return nil, fmt.Errorf("failed to parse problemset: %w", err)
	}

	// 使用文件名作为唯一 ID，确保与列表接口一致
	ps.ID = id

	s.setCache(cacheKey, &ps)
	return &ps, nil
}

// ClearCache 清除缓存
func (s *ProblemSetService) ClearCache() {
	s.cacheLock.Lock()
	defer s.cacheLock.Unlock()

	s.cache = make(map[string]CacheItem)
}