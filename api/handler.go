package api

import (
	"fmt"
	"net/http"
	"strings"

	"cfProblemList/models"
	"cfProblemList/service"

	"github.com/gin-gonic/gin"
)

// Handler API处理器
type Handler struct {
	psService       *service.ProblemSetService
	authService     *service.AuthService
	progressService *service.ProgressService
	followService   *service.FollowService
}

// NewHandler 创建新的Handler
func NewHandler() *Handler {
	return &Handler{
		psService:       service.NewProblemSetService(),
		authService:     service.NewAuthService(),
		progressService: service.NewProgressService(),
		followService:   service.NewFollowService(),
	}
}

// successResponse 成功响应
func successResponse(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, models.Response{
		Code:    0,
		Message: "success",
		Data:    data,
	})
}

// errorResponse 错误响应
func errorResponse(c *gin.Context, code int, message string) {
	c.JSON(code, models.Response{
		Code:    code,
		Message: message,
	})
}

// ==================== 题单相关接口 ====================

// GetProblemSetList 获取题单列表
func (h *Handler) GetProblemSetList(c *gin.Context) {
	summaries, err := h.psService.GetProblemSetList()
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}
	successResponse(c, summaries)
}

// GetProblemSetByID 获取单个题单详情
func (h *Handler) GetProblemSetByID(c *gin.Context) {
	id := c.Param("id")
	if id == "" {
		errorResponse(c, http.StatusBadRequest, "missing problemset id")
		return
	}

	ps, err := h.psService.GetProblemSetByID(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			errorResponse(c, http.StatusNotFound, err.Error())
			return
		}
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, ps)
}

// ==================== 用户认证接口 ====================

// Register 用户注册
func (h *Handler) Register(c *gin.Context) {
	var req models.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		errorResponse(c, http.StatusBadRequest, "参数错误: "+err.Error())
		return
	}

	user, err := h.authService.Register(&req)
	if err != nil {
		errorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	successResponse(c, gin.H{
		"id":       user.ID,
		"username": user.Username,
		"email":    user.Email,
		"nickname": user.Nickname,
	})
}

// Login 用户登录
func (h *Handler) Login(c *gin.Context) {
	var req models.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		errorResponse(c, http.StatusBadRequest, "参数错误")
		return
	}

	resp, err := h.authService.Login(&req)
	if err != nil {
		errorResponse(c, http.StatusUnauthorized, err.Error())
		return
	}

	successResponse(c, resp)
}

// GetCurrentUser 获取当前用户信息
func (h *Handler) GetCurrentUser(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	user, err := h.authService.GetUserByID(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusNotFound, "用户不存在")
		return
	}

	successResponse(c, user)
}

// ==================== 进度管理接口 ====================

// UpdateProgress 更新题目进度
func (h *Handler) UpdateProgress(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	var req models.UpdateProgressRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		errorResponse(c, http.StatusBadRequest, "参数错误")
		return
	}

	progress, err := h.progressService.UpdateProgress(userID.(uint), &req)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, progress)
}

// GetProgress 获取单个题目进度
func (h *Handler) GetProgress(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	problemID := c.Query("problem_id")
	problemSetID := c.Query("problemset_id")

	if problemID == "" || problemSetID == "" {
		errorResponse(c, http.StatusBadRequest, "缺少参数")
		return
	}

	progress, err := h.progressService.GetProgress(userID.(uint), problemID, problemSetID)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	if progress == nil {
		successResponse(c, &models.ProgressResponse{IsCompleted: false})
	} else {
		successResponse(c, &models.ProgressResponse{IsCompleted: progress.IsCompleted})
	}
}

// GetProblemSetProgress 获取题单进度
func (h *Handler) GetProblemSetProgress(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	problemSetID := c.Param("id")
	if problemSetID == "" {
		errorResponse(c, http.StatusBadRequest, "缺少题单ID")
		return
	}

	progress, err := h.progressService.GetProblemSetProgress(userID.(uint), problemSetID)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, progress)
}

// GetAllProblemSetProgress 获取所有题单进度
func (h *Handler) GetAllProblemSetProgress(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	progress, err := h.progressService.GetAllProblemSetProgress(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, progress)
}

// GetUserStats 获取用户总体统计
func (h *Handler) GetUserStats(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	stats, err := h.progressService.GetUserStats(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, stats)
}

// GetCategoryProgress 获取分类进度
func (h *Handler) GetCategoryProgress(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	progress, err := h.progressService.GetCategoryProgress(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, progress)
}

// GetHeatmapData 获取热力图数据
func (h *Handler) GetHeatmapData(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	data, err := h.progressService.GetHeatmapData(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, data)
}

// GetDetailedStats 获取详细统计
func (h *Handler) GetDetailedStats(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	stats, err := h.progressService.GetDetailedStats(userID.(uint))
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, stats)
}

// ==================== 中间件 ====================

// AuthMiddleware JWT认证中间件
func (h *Handler) AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, models.Response{
				Code:    401,
				Message: "未提供认证信息",
			})
			c.Abort()
			return
		}

		// Bearer token格式
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, models.Response{
				Code:    401,
				Message: "认证格式错误",
			})
			c.Abort()
			return
		}

		claims, err := h.authService.ValidateToken(parts[1])
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.Response{
				Code:    401,
				Message: "Token无效或已过期",
			})
			c.Abort()
			return
		}

		// 将用户信息存入上下文
		c.Set("userID", claims.UserID)
		c.Set("username", claims.Username)
		c.Next()
	}
}

// ==================== 用户交互接口 ====================

// SearchUsers 搜索用户
func (h *Handler) SearchUsers(c *gin.Context) {
	keyword := c.Query("keyword")
	page := 1
	pageSize := 20

	// 尝试获取当前用户ID（可选）
	var viewerID uint
	if userID, exists := c.Get("userID"); exists {
		viewerID = userID.(uint)
	}

	result, err := h.followService.SearchUsers(viewerID, keyword, page, pageSize)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, result)
}

// GetUserProfile 获取用户公开资料
func (h *Handler) GetUserProfile(c *gin.Context) {
	targetUserIDStr := c.Param("id")
	if targetUserIDStr == "" {
		errorResponse(c, http.StatusBadRequest, "缺少用户ID")
		return
	}

	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	// 尝试获取当前用户ID（可选）
	var viewerID uint
	if userID, exists := c.Get("userID"); exists {
		viewerID = userID.(uint)
	}

	profile, err := h.followService.GetUserProfile(viewerID, targetUserID)
	if err != nil {
		errorResponse(c, http.StatusNotFound, err.Error())
		return
	}

	successResponse(c, profile)
}

// GetUserHeatmap 获取用户热力图（公开）
func (h *Handler) GetUserHeatmap(c *gin.Context) {
	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	data, err := h.progressService.GetHeatmapData(targetUserID)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, data)
}

// GetUserDetailStats 获取用户详细统计（公开）
func (h *Handler) GetUserDetailStats(c *gin.Context) {
	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	stats, err := h.progressService.GetDetailedStats(targetUserID)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, stats)
}

// FollowUser 关注用户
func (h *Handler) FollowUser(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	if err := h.followService.FollowUser(userID.(uint), targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	successResponse(c, gin.H{"message": "关注成功"})
}

// UnfollowUser 取消关注
func (h *Handler) UnfollowUser(c *gin.Context) {
	userID, exists := c.Get("userID")
	if !exists {
		errorResponse(c, http.StatusUnauthorized, "未登录")
		return
	}

	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	if err := h.followService.UnfollowUser(userID.(uint), targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, err.Error())
		return
	}

	successResponse(c, gin.H{"message": "取消关注成功"})
}

// GetFollowers 获取粉丝列表
func (h *Handler) GetFollowers(c *gin.Context) {
	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	// 尝试获取当前用户ID（可选）
	var viewerID uint
	if userID, exists := c.Get("userID"); exists {
		viewerID = userID.(uint)
	}

	page := 1
	pageSize := 20

	result, err := h.followService.GetFollowers(viewerID, targetUserID, page, pageSize)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, result)
}

// GetFollowings 获取关注列表
func (h *Handler) GetFollowings(c *gin.Context) {
	targetUserIDStr := c.Param("id")
	var targetUserID uint
	if _, err := fmt.Sscanf(targetUserIDStr, "%d", &targetUserID); err != nil {
		errorResponse(c, http.StatusBadRequest, "无效的用户ID")
		return
	}

	// 尝试获取当前用户ID（可选）
	var viewerID uint
	if userID, exists := c.Get("userID"); exists {
		viewerID = userID.(uint)
	}

	page := 1
	pageSize := 20

	result, err := h.followService.GetFollowings(viewerID, targetUserID, page, pageSize)
	if err != nil {
		errorResponse(c, http.StatusInternalServerError, err.Error())
		return
	}

	successResponse(c, result)
}