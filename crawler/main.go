package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"sort"
	"time"
)

// APIProblem 表示 API 返回的题目
type APIProblem struct {
	ContestID int      `json:"contestId"`
	Index     string   `json:"index"`
	Name      string   `json:"name"`
	Type      string   `json:"type"`
	Rating    int      `json:"rating"`
	Tags      []string `json:"tags"`
}

// APIResult 表示 API 返回的结果
type APIResult struct {
	Status  string `json:"status"`
	Comment string `json:"comment,omitempty"`
	Result  struct {
		Problems []APIProblem `json:"problems"`
	} `json:"result"`
}

// Problem 表示我们存储的题目格式
type Problem struct {
	ID         string   `json:"id"`
	ContestID  int      `json:"contest_id"`
	Index      string   `json:"index"`
	Name       string   `json:"name"`
	Difficulty int      `json:"difficulty"`
	Tags       []string `json:"tags"`
	URL        string   `json:"url"`
}

// ProblemSet 表示题目集
type ProblemSet struct {
	TotalProblems int       `json:"total_problems"`
	LastUpdated   string    `json:"last_updated"`
	Problems      []Problem `json:"problems"`
	ByDifficulty  map[string]int `json:"by_difficulty"`
	ByTag         map[string]int `json:"by_tag"`
}

const (
	apiURL       = "https://codeforces.com/api/problemset.problems"
	outputDir    = "data/cf-problems"
)

func main() {
	fmt.Println("🐰 开始从 Codeforces API 获取题库...")

	// 创建输出目录
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		fmt.Printf("❌ 创建目录失败: %v\n", err)
		return
	}

	client := &http.Client{
		Timeout: 60 * time.Second,
	}

	// 调用 API
	fmt.Println("📡 正在请求 Codeforces API...")
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		fmt.Printf("❌ 创建请求失败: %v\n", err)
		return
	}
	
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("❌ API 请求失败: %v\n", err)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("❌ 读取响应失败: %v\n", err)
		return
	}

	// 解析 API 响应
	var apiResult APIResult
	if err := json.Unmarshal(body, &apiResult); err != nil {
		fmt.Printf("❌ 解析 JSON 失败: %v\n", err)
		return
	}

	if apiResult.Status != "OK" {
		fmt.Printf("❌ API 返回错误: %s\n", apiResult.Comment)
		return
	}

	fmt.Printf("✅ 获取到 %d 道题目\n", len(apiResult.Result.Problems))

	// 转换数据格式
	problems := make([]Problem, 0, len(apiResult.Result.Problems))
	byDifficulty := make(map[string]int)
	byTag := make(map[string]int)

	for _, p := range apiResult.Result.Problems {
		problem := Problem{
			ID:         fmt.Sprintf("%d%s", p.ContestID, p.Index),
			ContestID:  p.ContestID,
			Index:      p.Index,
			Name:       p.Name,
			Difficulty: p.Rating,
			Tags:       p.Tags,
			URL:        fmt.Sprintf("https://codeforces.com/problemset/problem/%d/%s", p.ContestID, p.Index),
		}
		problems = append(problems, problem)

		// 统计难度分布
		if p.Rating > 0 {
			diffRange := getDifficultyRange(p.Rating)
			byDifficulty[diffRange]++
		} else {
			byDifficulty["Unrated"]++
		}

		// 统计标签分布
		for _, tag := range p.Tags {
			byTag[tag]++
		}
	}

	// 按题目 ID 排序
	sort.Slice(problems, func(i, j int) bool {
		if problems[i].ContestID != problems[j].ContestID {
			return problems[i].ContestID > problems[j].ContestID
		}
		return problems[i].Index < problems[j].Index
	})

	// 保存结果
	problemSet := ProblemSet{
		TotalProblems: len(problems),
		LastUpdated:   time.Now().Format("2006-01-02 15:04:05"),
		Problems:      problems,
		ByDifficulty:  byDifficulty,
		ByTag:         byTag,
	}

	outputPath := fmt.Sprintf("%s/problems.json", outputDir)
	data, err := json.MarshalIndent(problemSet, "", "  ")
	if err != nil {
		fmt.Printf("❌ 序列化失败: %v\n", err)
		return
	}

	if err := os.WriteFile(outputPath, data, 0644); err != nil {
		fmt.Printf("❌ 写入文件失败: %v\n", err)
		return
	}

	fmt.Printf("\n🎉 抓取完成！\n")
	fmt.Printf("   📊 总题目数: %d\n", len(problems))
	fmt.Printf("   📁 保存位置: %s\n", outputPath)
	
	// 显示难度分布
	fmt.Println("\n📈 难度分布:")
	for _, r := range []string{"800-999", "1000-1199", "1200-1399", "1400-1599", "1600-1799", "1800-1999", "2000-2199", "2200-2399", "2400-2599", "2600-2799", "2800-2999", "3000+", "Unrated"} {
		if count, ok := byDifficulty[r]; ok && count > 0 {
			fmt.Printf("   %s: %d 道\n", r, count)
		}
	}

	// 显示热门标签
	fmt.Println("\n🏷️ 热门标签 (Top 10):")
	type tagCount struct {
		tag   string
		count int
	}
	var tags []tagCount
	for t, c := range byTag {
		tags = append(tags, tagCount{t, c})
	}
	sort.Slice(tags, func(i, j int) bool { return tags[i].count > tags[j].count })
	for i := 0; i < 10 && i < len(tags); i++ {
		fmt.Printf("   %s: %d 道\n", tags[i].tag, tags[i].count)
	}
}

func getDifficultyRange(rating int) string {
	switch {
	case rating < 1000:
		return "800-999"
	case rating < 1200:
		return "1000-1199"
	case rating < 1400:
		return "1200-1399"
	case rating < 1600:
		return "1400-1599"
	case rating < 1800:
		return "1600-1799"
	case rating < 2000:
		return "1800-1999"
	case rating < 2200:
		return "2000-2199"
	case rating < 2400:
		return "2200-2399"
	case rating < 2600:
		return "2400-2599"
	case rating < 2800:
		return "2600-2799"
	case rating < 3000:
		return "2800-2999"
	default:
		return "3000+"
	}
}