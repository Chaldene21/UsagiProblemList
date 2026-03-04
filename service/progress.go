package service

import (
	"cfProblemList/models"
	"time"

	"gorm.io/gorm"
)

// ProgressService 进度服务
type ProgressService struct {
	db *gorm.DB
}

// NewProgressService 创建进度服务
func NewProgressService() *ProgressService {
	return &ProgressService{
		db: GetDB(),
	}
}

// UpdateProgress 更新题目进度
func (s *ProgressService) UpdateProgress(userID uint, req *models.UpdateProgressRequest) (*models.ProblemProgress, error) {
	var progress models.ProblemProgress

	// 查找现有进度
	err := s.db.Where("user_id = ? AND problem_id = ? AND problemset_id = ?",
		userID, req.ProblemID, req.ProblemSetID).First(&progress).Error

	if err == gorm.ErrRecordNotFound {
		// 创建新进度
		progress = models.ProblemProgress{
			UserID:       userID,
			ProblemID:    req.ProblemID,
			ProblemSetID: req.ProblemSetID,
			IsCompleted:  req.IsCompleted,
		}
		if req.IsCompleted {
			progress.CompletedAt = time.Now()
		}
		if err := s.db.Create(&progress).Error; err != nil {
			return nil, err
		}
	} else if err != nil {
		return nil, err
	} else {
		// 更新现有进度
		progress.IsCompleted = req.IsCompleted
		if req.IsCompleted {
			progress.CompletedAt = time.Now()
		} else {
			progress.CompletedAt = time.Time{}
		}
		if err := s.db.Save(&progress).Error; err != nil {
			return nil, err
		}
	}

	return &progress, nil
}

// GetProgress 获取单个题目进度
func (s *ProgressService) GetProgress(userID uint, problemID, problemSetID string) (*models.ProblemProgress, error) {
	var progress models.ProblemProgress
	err := s.db.Where("user_id = ? AND problem_id = ? AND problemset_id = ?",
		userID, problemID, problemSetID).First(&progress).Error
	if err == gorm.ErrRecordNotFound {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &progress, nil
}

// GetUserProblemSetProgress 获取用户在某个题单的所有进度
func (s *ProgressService) GetUserProblemSetProgress(userID uint, problemSetID string) ([]models.ProblemProgress, error) {
	var progressList []models.ProblemProgress
	err := s.db.Where("user_id = ? AND problemset_id = ?", userID, problemSetID).Find(&progressList).Error
	return progressList, err
}

// GetUserAllProgress 获取用户所有进度
func (s *ProgressService) GetUserAllProgress(userID uint) ([]models.ProblemProgress, error) {
	var progressList []models.ProblemProgress
	err := s.db.Where("user_id = ?", userID).Find(&progressList).Error
	return progressList, err
}

// GetUserStats 获取用户总体统计
func (s *ProgressService) GetUserStats(userID uint) (*models.UserStats, error) {
	stats := &models.UserStats{}

	// 获取用户所有完成的进度
	var completedCount int64
	s.db.Model(&models.ProblemProgress{}).
		Where("user_id = ? AND is_completed = ?", userID, true).
		Count(&completedCount)
	stats.CompletedProblems = int(completedCount)

	// 获取所有完成的题目ID和难度
	var completedProblems []struct {
		ProblemID string
	}
	s.db.Model(&models.ProblemProgress{}).
		Select("problem_id").
		Where("user_id = ? AND is_completed = ?", userID, true).
		Find(&completedProblems)

	// 简化统计 - 只返回完成数量
	stats.TotalProblems = 0
	stats.TotalProblemSets = 0
	stats.CompletedSets = 0
	stats.EasyCount = 0
	stats.MediumCount = 0
	stats.HardCount = 0

	return stats, nil
}

// GetProblemSetProgress 获取题单进度详情
func (s *ProgressService) GetProblemSetProgress(userID uint, problemSetID string) (*models.ProblemSetProgress, error) {
	psService := NewProblemSetService()
	ps, err := psService.GetProblemSetByID(problemSetID)
	if err != nil {
		return nil, err
	}

	// 简化：不查询具体进度，直接返回基本信息
	totalProblems := 0
	for _, section := range ps.Sections {
		for _, content := range section.Content {
			totalProblems += len(content.Problems)
		}
	}

	return &models.ProblemSetProgress{
		ProblemSetID:      problemSetID,
		ProblemSetTitle:   ps.Title,
		Category:          ps.Category,
		TotalProblems:     totalProblems,
		CompletedProblems: 0,
		Percentage:        0,
		CompletedIDs:      []string{},
	}, nil
}

// GetAllProblemSetProgress 获取所有题单进度
func (s *ProgressService) GetAllProblemSetProgress(userID uint) ([]models.ProblemSetProgress, error) {
	psService := NewProblemSetService()
	summaries, err := psService.GetProblemSetList()
	if err != nil {
		return nil, err
	}

	var result []models.ProblemSetProgress
	for _, summary := range summaries {
		progress, err := s.GetProblemSetProgress(userID, summary.ID)
		if err != nil {
			continue
		}
		result = append(result, *progress)
	}

	return result, nil
}

// GetCategoryProgress 获取分类进度
func (s *ProgressService) GetCategoryProgress(userID uint) ([]models.CategoryProgress, error) {
	psService := NewProblemSetService()
	summaries, err := psService.GetProblemSetList()
	if err != nil {
		return nil, err
	}

	progressList, err := s.GetUserAllProgress(userID)
	if err != nil {
		return nil, err
	}

	completedMap := make(map[string]bool)
	for _, p := range progressList {
		if p.IsCompleted {
			completedMap[p.ProblemID] = true
		}
	}

	// 按分类统计
	categoryStats := make(map[string]struct{ total, completed int })

	for _, summary := range summaries {
		ps, err := psService.GetProblemSetByID(summary.ID)
		if err != nil {
			continue
		}

		if _, exists := categoryStats[ps.Category]; !exists {
			categoryStats[ps.Category] = struct{ total, completed int }{0, 0}
		}

		stats := categoryStats[ps.Category]
		for _, section := range ps.Sections {
			for _, content := range section.Content {
				for _, problem := range content.Problems {
					stats.total++
					if completedMap[problem.ID] {
						stats.completed++
					}
				}
			}
		}
		categoryStats[ps.Category] = stats
	}

	var result []models.CategoryProgress
	for category, stats := range categoryStats {
		percentage := 0
		if stats.total > 0 {
			percentage = (stats.completed * 100) / stats.total
		}
		result = append(result, models.CategoryProgress{
			Category:          category,
			TotalProblems:     stats.total,
			CompletedProblems: stats.completed,
			Percentage:        percentage,
		})
	}

	return result, nil
}