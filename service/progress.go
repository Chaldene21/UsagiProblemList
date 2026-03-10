package service

import (
	"cfProblemList/models"
	"fmt"
	"sort"
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

	// 获取所有题目
	var allProblems []models.Problem
	var completedIDs []string
	for _, section := range ps.Sections {
		for _, content := range section.Content {
			allProblems = append(allProblems, content.Problems...)
		}
	}

	// 获取用户完成的题目
	var progressList []models.ProblemProgress
	s.db.Where("user_id = ? AND problemset_id = ? AND is_completed = ?", userID, problemSetID, true).
		Find(&progressList)

	completedMap := make(map[string]bool)
	for _, p := range progressList {
		completedMap[p.ProblemID] = true
		completedIDs = append(completedIDs, p.ProblemID)
	}

	completedCount := len(completedIDs)
	totalProblems := len(allProblems)
	percentage := 0
	if totalProblems > 0 {
		percentage = (completedCount * 100) / totalProblems
	}

	return &models.ProblemSetProgress{
		ProblemSetID:      problemSetID,
		ProblemSetTitle:   ps.Title,
		Category:          ps.Category,
		TotalProblems:     totalProblems,
		CompletedProblems: completedCount,
		Percentage:        percentage,
		CompletedIDs:      completedIDs,
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

// GetHeatmapData 获取热力图数据（最近一年）
func (s *ProgressService) GetHeatmapData(userID uint) ([]models.HeatmapData, error) {
	// 获取最近一年的完成记录
	oneYearAgo := time.Now().AddDate(-1, 0, 0)

	var progressList []models.ProblemProgress
	err := s.db.Where("user_id = ? AND is_completed = ? AND completed_at > ?",
		userID, true, oneYearAgo).
		Order("completed_at ASC").
		Find(&progressList).Error
	if err != nil {
		return nil, err
	}

	// 按日期统计
	dateCount := make(map[string]int)
	for _, p := range progressList {
		if !p.CompletedAt.IsZero() {
			date := p.CompletedAt.Format("2006-01-02")
			dateCount[date]++
		}
	}

	// 生成最近365天的数据
	var result []models.HeatmapData
	now := time.Now()

	// 计算最大值用于确定热度等级
	maxCount := 0
	for _, count := range dateCount {
		if count > maxCount {
			maxCount = count
		}
	}

	for i := 364; i >= 0; i-- {
		date := now.AddDate(0, 0, -i)
		dateStr := date.Format("2006-01-02")
		count := dateCount[dateStr]

		// 计算热度等级 (0-4)
		level := 0
		if maxCount > 0 && count > 0 {
			level = (count * 4) / maxCount
			if level > 4 {
				level = 4
			}
			if level == 0 && count > 0 {
				level = 1
			}
		}

		result = append(result, models.HeatmapData{
			Date:      dateStr,
			Count:     count,
			Level:     level,
			Timestamp: date.Unix(),
		})
	}

	return result, nil
}

// GetDetailedStats 获取详细统计数据
func (s *ProgressService) GetDetailedStats(userID uint) (*models.DetailedStats, error) {
	stats := &models.DetailedStats{}

	// 获取所有题单的题目信息
	psService := NewProblemSetService()
	summaries, err := psService.GetProblemSetList()
	if err != nil {
		return nil, err
	}

	// 统计所有题目及其难度
	allProblems := make(map[string]models.Problem) // problemID -> Problem
	for _, summary := range summaries {
		ps, err := psService.GetProblemSetByID(summary.ID)
		if err != nil {
			continue
		}
		for _, section := range ps.Sections {
			for _, content := range section.Content {
				for _, problem := range content.Problems {
					allProblems[problem.ID] = problem
				}
			}
		}
	}

	stats.TotalProblems = len(allProblems)

	// 统计各难度总数
	for _, p := range allProblems {
		if p.Difficulty < 1300 {
			stats.EasyTotal++
		} else if p.Difficulty < 1700 {
			stats.MediumTotal++
		} else {
			stats.HardTotal++
		}
	}

	// 获取用户完成的题目
	var progressList []models.ProblemProgress
	s.db.Where("user_id = ? AND is_completed = ?", userID, true).
		Order("completed_at DESC").
		Find(&progressList)

	completedMap := make(map[string]bool)
	var recentActivities []models.ActivityItem

	for _, p := range progressList {
		if completedMap[p.ProblemID] {
			continue
		}
		completedMap[p.ProblemID] = true
		stats.TotalCompleted++

		// 统计各难度完成数
		if problem, exists := allProblems[p.ProblemID]; exists {
			if problem.Difficulty < 1300 {
				stats.EasyCompleted++
			} else if problem.Difficulty < 1700 {
				stats.MediumCompleted++
			} else {
				stats.HardCompleted++
			}

			// 收集最近活动
			if len(recentActivities) < 10 && !p.CompletedAt.IsZero() {
				recentActivities = append(recentActivities, models.ActivityItem{
					ProblemID:   p.ProblemID,
					ProblemName: problem.Name,
					Difficulty:  problem.Difficulty,
					CompletedAt: p.CompletedAt,
				})
			}
		}
	}
	stats.RecentActivities = recentActivities

	// 计算连续天数
	stats.CurrentStreak, stats.MaxStreak, stats.TotalDays = s.calculateStreaks(progressList)

	return stats, nil
}

// calculateStreaks 计算连续刷题天数
func (s *ProgressService) calculateStreaks(progressList []models.ProblemProgress) (currentStreak, maxStreak, totalDays int) {
	if len(progressList) == 0 {
		return 0, 0, 0
	}

	// 按日期分组
	dateSet := make(map[string]bool)
	for _, p := range progressList {
		if !p.CompletedAt.IsZero() {
			date := p.CompletedAt.Format("2006-01-02")
			dateSet[date] = true
		}
	}

	totalDays = len(dateSet)

	// 获取所有日期并排序
	var dates []time.Time
	for dateStr := range dateSet {
		t, _ := time.Parse("2006-01-02", dateStr)
		dates = append(dates, t)
	}
	sort.Slice(dates, func(i, j int) bool {
		return dates[i].Before(dates[j])
	})

	if len(dates) == 0 {
		return 0, 0, 0
	}

	// 计算最大连续天数
	maxStreak = 1
	currentStreak = 1
	for i := 1; i < len(dates); i++ {
		if dates[i].Sub(dates[i-1]) == 24*time.Hour {
			currentStreak++
			if currentStreak > maxStreak {
				maxStreak = currentStreak
			}
		} else {
			currentStreak = 1
		}
	}

	// 计算当前连续天数（从今天往前数）
	now := time.Now()
	today := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())

	currentStreak = 0
	for i := 0; i <= 365; i++ {
		checkDate := today.AddDate(0, 0, -i)
		dateStr := checkDate.Format("2006-01-02")
		if dateSet[dateStr] {
			currentStreak++
		} else if i > 0 { // 允许今天还没做题
			break
		}
	}

	// 如果今天没做题，检查昨天开始的连续
	if currentStreak == 0 {
		yesterday := today.AddDate(0, 0, -1)
		for i := 0; i <= 365; i++ {
			checkDate := yesterday.AddDate(0, 0, -i)
			dateStr := checkDate.Format("2006-01-02")
			if dateSet[dateStr] {
				currentStreak++
			} else {
				break
			}
		}
	}

	return currentStreak, maxStreak, totalDays
}

// Debug function
func (s *ProgressService) DebugPrintProgress(userID uint) {
	var progressList []models.ProblemProgress
	s.db.Where("user_id = ?", userID).Find(&progressList)
	fmt.Printf("Found %d progress records for user %d\n", len(progressList), userID)
	for _, p := range progressList {
		fmt.Printf("  ProblemID: %s, Completed: %v, CompletedAt: %v\n", p.ProblemID, p.IsCompleted, p.CompletedAt)
	}
}