package service

import (
	"errors"
	"time"

	"cfProblemList/models"

	"gorm.io/gorm"
)

// FollowService 用户交互服务
type FollowService struct {
	db *gorm.DB
}

// NewFollowService 创建用户交互服务
func NewFollowService() *FollowService {
	return &FollowService{
		db: GetDB(),
	}
}

// FollowUser 关注用户
func (s *FollowService) FollowUser(followerID, followingID uint) error {
	// 不能关注自己
	if followerID == followingID {
		return errors.New("不能关注自己")
	}

	// 检查是否已关注
	var existingFollow models.Follow
	err := s.db.Where("follower_id = ? AND following_id = ?", followerID, followingID).First(&existingFollow).Error
	if err == nil {
		return errors.New("已经关注了该用户")
	}

	// 检查被关注用户是否存在
	var targetUser models.User
	if err := s.db.First(&targetUser, followingID).Error; err != nil {
		return errors.New("用户不存在")
	}

	// 创建关注关系
	follow := models.Follow{
		FollowerID:  followerID,
		FollowingID: followingID,
		CreatedAt:   time.Now(),
	}

	return s.db.Create(&follow).Error
}

// UnfollowUser 取消关注
func (s *FollowService) UnfollowUser(followerID, followingID uint) error {
	result := s.db.Where("follower_id = ? AND following_id = ?", followerID, followingID).
		Delete(&models.Follow{})

	if result.RowsAffected == 0 {
		return errors.New("未关注该用户")
	}

	return result.Error
}

// IsFollowing 检查是否关注了某用户
func (s *FollowService) IsFollowing(followerID, followingID uint) bool {
	var follow models.Follow
	err := s.db.Where("follower_id = ? AND following_id = ?", followerID, followingID).First(&follow).Error
	return err == nil
}

// GetUserProfile 获取用户公开资料
func (s *FollowService) GetUserProfile(viewerID, targetUserID uint) (*models.UserProfile, error) {
	// 获取目标用户信息
	var targetUser models.User
	if err := s.db.First(&targetUser, targetUserID).Error; err != nil {
		return nil, errors.New("用户不存在")
	}

	profile := &models.UserProfile{
		ID:        targetUser.ID,
		Username:  targetUser.Username,
		Nickname:  targetUser.Nickname,
		Avatar:    targetUser.Avatar,
		CreatedAt: targetUser.CreatedAt.Format("2006-01-02"),
	}

	// 获取关注数和粉丝数
	var followersCount, followingsCount int64
	s.db.Model(&models.Follow{}).Where("following_id = ?", targetUserID).Count(&followersCount)
	s.db.Model(&models.Follow{}).Where("follower_id = ?", targetUserID).Count(&followingsCount)
	profile.FollowersCount = int(followersCount)
	profile.FollowingsCount = int(followingsCount)

	// 获取刷题统计
	progressService := NewProgressService()
	stats, err := progressService.GetDetailedStats(targetUserID)
	if err == nil {
		profile.TotalCompleted = stats.TotalCompleted
		profile.CurrentStreak = stats.CurrentStreak
		profile.MaxStreak = stats.MaxStreak
	}

	// 如果有查看者，检查关注关系
	if viewerID > 0 {
		profile.IsFollowing = s.IsFollowing(viewerID, targetUserID)
		profile.IsFollower = s.IsFollowing(targetUserID, viewerID)
	}

	return profile, nil
}

// SearchUsers 搜索用户
func (s *FollowService) SearchUsers(viewerID uint, keyword string, page, pageSize int) (*models.FollowListResponse, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 50 {
		pageSize = 20
	}

	var users []models.User
	var total int64

	// 构建查询
	query := s.db.Model(&models.User{})
	if keyword != "" {
		query = query.Where("username LIKE ? OR nickname LIKE ?", "%"+keyword+"%", "%"+keyword+"%")
	}

	// 获取总数
	query.Count(&total)

	// 分页查询
	offset := (page - 1) * pageSize
	if err := query.Order("id DESC").Offset(offset).Limit(pageSize).Find(&users).Error; err != nil {
		return nil, err
	}

	// 确保返回空数组而不是 null
	profiles := make([]models.UserProfile, 0)
	for _, user := range users {
		profile := models.UserProfile{
			ID:        user.ID,
			Username:  user.Username,
			Nickname:  user.Nickname,
			Avatar:    user.Avatar,
			CreatedAt: user.CreatedAt.Format("2006-01-02"),
		}

		// 获取完成题目数
		var completedCount int64
		s.db.Model(&models.ProblemProgress{}).
			Where("user_id = ? AND is_completed = ?", user.ID, true).
			Count(&completedCount)
		profile.TotalCompleted = int(completedCount)

		// 检查关注状态
		if viewerID > 0 {
			profile.IsFollowing = s.IsFollowing(viewerID, user.ID)
			profile.IsFollower = s.IsFollowing(user.ID, viewerID)
		}

		profiles = append(profiles, profile)
	}

	return &models.FollowListResponse{
		Users:    profiles,
		Total:    int(total),
		Page:     page,
		PageSize: pageSize,
	}, nil
}

// GetFollowers 获取粉丝列表
func (s *FollowService) GetFollowers(viewerID, targetUserID uint, page, pageSize int) (*models.FollowListResponse, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 50 {
		pageSize = 20
	}

	var total int64
	s.db.Model(&models.Follow{}).Where("following_id = ?", targetUserID).Count(&total)

	var follows []models.Follow
	offset := (page - 1) * pageSize
	if err := s.db.Where("following_id = ?", targetUserID).
		Order("created_at DESC").
		Offset(offset).Limit(pageSize).
		Find(&follows).Error; err != nil {
		return nil, err
	}

	// 确保返回空数组而不是 null
	profiles := make([]models.UserProfile, 0)
	for _, follow := range follows {
		profile, err := s.GetUserProfile(viewerID, follow.FollowerID)
		if err != nil {
			continue
		}
		profiles = append(profiles, *profile)
	}

	return &models.FollowListResponse{
		Users:    profiles,
		Total:    int(total),
		Page:     page,
		PageSize: pageSize,
	}, nil
}

// GetFollowings 获取关注列表
func (s *FollowService) GetFollowings(viewerID, targetUserID uint, page, pageSize int) (*models.FollowListResponse, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 50 {
		pageSize = 20
	}

	var total int64
	s.db.Model(&models.Follow{}).Where("follower_id = ?", targetUserID).Count(&total)

	var follows []models.Follow
	offset := (page - 1) * pageSize
	if err := s.db.Where("follower_id = ?", targetUserID).
		Order("created_at DESC").
		Offset(offset).Limit(pageSize).
		Find(&follows).Error; err != nil {
		return nil, err
	}

	// 确保返回空数组而不是 null
	profiles := make([]models.UserProfile, 0)
	for _, follow := range follows {
		profile, err := s.GetUserProfile(viewerID, follow.FollowingID)
		if err != nil {
			continue
		}
		profiles = append(profiles, *profile)
	}

	return &models.FollowListResponse{
		Users:    profiles,
		Total:    int(total),
		Page:     page,
		PageSize: pageSize,
	}, nil
}

// GetUserStats 获取用户统计信息（关注数、粉丝数）
func (s *FollowService) GetUserStats(userID uint) (followersCount, followingsCount int) {
	var fc, fc2 int64
	s.db.Model(&models.Follow{}).Where("following_id = ?", userID).Count(&fc)
	s.db.Model(&models.Follow{}).Where("follower_id = ?", userID).Count(&fc2)
	return int(fc), int(fc2)
}