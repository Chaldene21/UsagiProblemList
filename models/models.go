package models

import (
	"time"

	"gorm.io/gorm"
)

// Problem 表示单个题目
type Problem struct {
	ID         string   `json:"id"`
	Name       string   `json:"name"`
	Difficulty int      `json:"difficulty"`
	Tags       []string `json:"tags"`
	URL        string   `json:"url"`
	Note       string   `json:"note"`
}

// SubSection 表示子章节
type SubSection struct {
	Type         string    `json:"type,omitempty"`         // "paragraph" 或空（子章节对象）
	Text         string    `json:"text,omitempty"`         // 段落文本
	Title        string    `json:"title,omitempty"`        // 子章节标题
	Idea         string    `json:"idea,omitempty"`         // 解题思路
	CodeTemplate string    `json:"code_template,omitempty"` // 代码模板
	Problems     []Problem `json:"problems,omitempty"`     // 题目列表
}

// Section 表示顶级章节
type Section struct {
	Title   string       `json:"title"`
	Content []SubSection `json:"content"`
}

// ProblemSet 表示完整题单
type ProblemSet struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Category    string    `json:"category"`
	Sections    []Section `json:"sections"`
}

// ProblemSetSummary 表示题单简要信息（用于列表页）
type ProblemSetSummary struct {
	ID          string `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Category    string `json:"category"`
}

// Response 表示统一响应格式
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// ==================== 数据库模型 ====================

// User 用户模型
type User struct {
	ID        uint           `json:"id" gorm:"primaryKey"`
	Username  string         `json:"username" gorm:"uniqueIndex;size:50;not null"`
	Email     string         `json:"email" gorm:"uniqueIndex;size:100;not null"`
	Password  string         `json:"-" gorm:"size:255;not null"`
	Nickname  string         `json:"nickname" gorm:"size:50"`
	Avatar    string         `json:"avatar" gorm:"size:255"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `json:"-" gorm:"index"`
}

// ProblemProgress 题目进度模型
type ProblemProgress struct {
	ID           uint      `json:"id" gorm:"primaryKey"`
	UserID       uint      `json:"user_id" gorm:"index;not null"`
	ProblemID    string    `json:"problem_id" gorm:"size:20;not null"` // 如 "1234A"
	ProblemSetID string    `json:"problemset_id" gorm:"size:50;not null"`
	IsCompleted  bool      `json:"is_completed" gorm:"default:false"`
	CompletedAt  time.Time `json:"completed_at"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`

	// 唯一索引：一个用户对一道题只能有一条进度记录
	UserProblem string `gorm:"uniqueIndex:idx_user_problem;size:100"`
}

// TableName 指定表名
func (ProblemProgress) TableName() string {
	return "problem_progress"
}

// BeforeCreate GORM钩子，设置UserProblem
func (p *ProblemProgress) BeforeCreate(tx *gorm.DB) error {
	p.UserProblem = string(rune(p.UserID)) + "_" + p.ProblemID
	return nil
}

// UserStats 用户统计数据
type UserStats struct {
	TotalProblems     int `json:"total_problems"`
	CompletedProblems int `json:"completed_problems"`
	TotalProblemSets  int `json:"total_problemsets"`
	CompletedSets     int `json:"completed_sets"`
	EasyCount         int `json:"easy_count"`
	MediumCount       int `json:"medium_count"`
	HardCount         int `json:"hard_count"`
}

// CategoryProgress 分类进度
type CategoryProgress struct {
	Category          string `json:"category"`
	TotalProblems     int    `json:"total_problems"`
	CompletedProblems int    `json:"completed_problems"`
	Percentage        int    `json:"percentage"`
}

// ProblemSetProgress 题单进度
type ProblemSetProgress struct {
	ProblemSetID      string   `json:"problemset_id"`
	ProblemSetTitle   string   `json:"problemset_title"`
	Category          string   `json:"category"`
	TotalProblems     int      `json:"total_problems"`
	CompletedProblems int      `json:"completed_problems"`
	Percentage        int      `json:"percentage"`
	CompletedIDs      []string `json:"completed_ids"`
}

// ==================== 请求/响应结构体 ====================

// RegisterRequest 注册请求
type RegisterRequest struct {
	Username string `json:"username" binding:"required,min=3,max=50"`
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required,min=6,max=50"`
	Nickname string `json:"nickname" binding:"max=50"`
}

// LoginRequest 登录请求
type LoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// LoginResponse 登录响应
type LoginResponse struct {
	Token    string `json:"token"`
	User     User   `json:"user"`
	Username string `json:"username"`
}

// UpdateProgressRequest 更新进度请求
type UpdateProgressRequest struct {
	ProblemID    string `json:"problem_id" binding:"required"`
	ProblemSetID string `json:"problemset_id" binding:"required"`
	IsCompleted  bool   `json:"is_completed"`
}

// ProgressResponse 进度响应
type ProgressResponse struct {
	IsCompleted bool `json:"is_completed"`
}

// HeatmapData 热力图数据
type HeatmapData struct {
	Date      string `json:"date"`       // 日期 YYYY-MM-DD
	Count     int    `json:"count"`      // 当天完成数量
	Level     int    `json:"level"`      // 热度等级 0-4
	Timestamp int64  `json:"timestamp"`  // Unix 时间戳
}

// DetailedStats 详细统计数据
type DetailedStats struct {
	TotalCompleted   int            `json:"total_completed"`
	TotalProblems    int            `json:"total_problems"`
	EasyCompleted    int            `json:"easy_completed"`
	EasyTotal        int            `json:"easy_total"`
	MediumCompleted  int            `json:"medium_completed"`
	MediumTotal      int            `json:"medium_total"`
	HardCompleted    int            `json:"hard_completed"`
	HardTotal        int            `json:"hard_total"`
	CurrentStreak    int            `json:"current_streak"`    // 当前连续天数
	MaxStreak        int            `json:"max_streak"`        // 最大连续天数
	TotalDays        int            `json:"total_days"`        // 总刷题天数
	RecentActivities []ActivityItem `json:"recent_activities"` // 最近活动
}

// ActivityItem 活动记录
type ActivityItem struct {
	ProblemID   string    `json:"problem_id"`
	ProblemName string    `json:"problem_name"`
	Difficulty  int       `json:"difficulty"`
	CompletedAt time.Time `json:"completed_at"`
}