package main

import (
	"fmt"
	"log"

	"cfProblemList/api"
	"cfProblemList/service"

	"github.com/gin-gonic/gin"
)

func main() {
	// 初始化数据库
	if err := service.InitDB(); err != nil {
		log.Fatal("Failed to initialize database:", err)
	}

	// 创建Handler
	handler := api.NewHandler()

	// 创建Gin路由
	r := gin.Default()

	// 静态文件服务
	r.Static("/static", "./static")
	r.StaticFile("/data/pictures/bg.png", "./data/pictures/bg.png")
	r.StaticFile("/", "./static/index.html")
	r.StaticFile("/favicon.ico", "./static/images/favicon.ico")

	// API路由组
	apiGroup := r.Group("/api")
	{
		// 公开接口 - 题单相关
		apiGroup.GET("/problemsets", handler.GetProblemSetList)
		apiGroup.GET("/problemsets/:id", handler.GetProblemSetByID)

		// 公开接口 - 用户认证
		apiGroup.POST("/register", handler.Register)
		apiGroup.POST("/login", handler.Login)

		// 公开接口 - 用户搜索和查看资料（可选认证）
		apiGroup.GET("/users/search", handler.SearchUsers)
		apiGroup.GET("/users/:id", handler.GetUserProfile)
		apiGroup.GET("/users/:id/heatmap", handler.GetUserHeatmap)
		apiGroup.GET("/users/:id/stats/detail", handler.GetUserDetailStats)
		apiGroup.GET("/users/:id/followers", handler.GetFollowers)
		apiGroup.GET("/users/:id/followings", handler.GetFollowings)

		// 需要认证的接口
		authGroup := apiGroup.Group("")
		authGroup.Use(handler.AuthMiddleware())
		{
			// 用户信息
			authGroup.GET("/user", handler.GetCurrentUser)

			// 进度管理
			authGroup.POST("/progress", handler.UpdateProgress)
			authGroup.GET("/progress", handler.GetProgress)
			authGroup.GET("/progress/problemset", handler.GetAllProblemSetProgress)
			authGroup.GET("/progress/problemset/:id", handler.GetProblemSetProgress)
			authGroup.GET("/progress/stats", handler.GetUserStats)
			authGroup.GET("/progress/category", handler.GetCategoryProgress)
			authGroup.GET("/progress/heatmap", handler.GetHeatmapData)
			authGroup.GET("/progress/detail", handler.GetDetailedStats)

			// 用户交互
			authGroup.POST("/users/:id/follow", handler.FollowUser)
			authGroup.DELETE("/users/:id/follow", handler.UnfollowUser)
		}
	}

	// 处理前端路由 - 所有非API和非静态文件请求返回index.html
	r.NoRoute(func(c *gin.Context) {
		c.File("./static/index.html")
	})

	// 启动服务器
	port := ":8080"
	fmt.Printf("🐰 Rabbit House Server starting on http://localhost%s\n", port)
	fmt.Println("Press Ctrl+C to stop")

	if err := r.Run(port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}