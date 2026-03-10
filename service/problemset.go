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

// GetProblemSetList 获取题单列表
func (s *ProblemSetService) GetProblemSetList() ([]models.ProblemSetSummary, error) {
	// 尝试从缓存获取
	if data, ok := s.getFromCache("list"); ok {
		return data.([]models.ProblemSetSummary), nil
	}

	var summaries []models.ProblemSetSummary

	// 尝试读取 index.json
	indexData, err := os.ReadFile(indexFile)
	if err == nil {
		if err := json.Unmarshal(indexData, &summaries); err == nil {
			s.setCache("list", summaries)
			return summaries, nil
		}
	}

	// 如果 index.json 不存在或读取失败，扫描目录
	files, err := os.ReadDir(dataDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read data directory: %w", err)
	}

	for _, file := range files {
		if file.IsDir() || filepath.Ext(file.Name()) != ".json" {
			continue
		}

		filePath := filepath.Join(dataDir, file.Name())
		data, err := os.ReadFile(filePath)
		if err != nil {
			continue
		}

		var ps models.ProblemSet
		if err := json.Unmarshal(data, &ps); err != nil {
			continue
		}

		summaries = append(summaries, models.ProblemSetSummary{
			ID:          ps.ID,
			Title:       ps.Title,
			Description: ps.Description,
			Category:    ps.Category,
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

	s.setCache(cacheKey, &ps)
	return &ps, nil
}

// ClearCache 清除缓存
func (s *ProblemSetService) ClearCache() {
	s.cacheLock.Lock()
	defer s.cacheLock.Unlock()

	s.cache = make(map[string]CacheItem)
}