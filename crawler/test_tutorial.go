package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"
)

var client *http.Client

func main() {
	client = &http.Client{
		Timeout: 30 * time.Second,
	}

	// 创建输出目录
	os.MkdirAll("data/cf-problems/tutorials", 0755)

	// 测试几个比赛的 editorial 页面
	testContests := []struct {
		contestID int
		name      string
	}{
		{2048, "Global Round 28"},
		{2193, "Educational Round 179"},
		{2047, "Global Round 27"},
	}

	for _, tc := range testContests {
		fmt.Printf("\n📚 测试比赛 %d (%s)\n", tc.contestID, tc.name)
		fmt.Println(strings.Repeat("-", 50))

		// 1. 获取比赛页面
		contestURL := fmt.Sprintf("https://codeforces.com/contest/%d", tc.contestID)
		html, err := fetchHTML(contestURL)
		if err != nil {
			fmt.Printf("❌ 获取比赛页面失败: %v\n", err)
			continue
		}

		// 2. 查找所有可能的 editorial 链接
		editorialURLs := findAllEditorialLinks(html, tc.contestID)
		fmt.Printf("🔍 找到 %d 个可能的 Editorial 链接\n", len(editorialURLs))
		for i, url := range editorialURLs {
			fmt.Printf("   [%d] %s\n", i+1, url)
		}

		// 3. 尝试每个链接，找到真正的题解内容
		for _, editorialURL := range editorialURLs {
			tutorialHTML, err := fetchHTML(editorialURL)
			if err != nil {
				fmt.Printf("   ❌ 获取失败: %v\n", err)
				continue
			}

			// 提取题解内容
			content := extractTutorialContent(tutorialHTML)
			
			// 检查是否包含真正的题解（包含题目解答说明）
			if isRealTutorial(content) {
				fmt.Printf("✅ 找到真正的题解: %s\n", editorialURL)
				fmt.Printf("   内容长度: %d 字符\n", len(content))
				
				// 提取各题的解法
				problems := extractProblemSolutions(content)
				fmt.Printf("   提取到 %d 道题的解法\n", len(problems))
				
				// 保存
				saveTutorial(tc.contestID, editorialURL, content, problems)
				break
			} else {
				fmt.Printf("   ⚠️ 不是题解页面（可能是公告）\n")
			}
		}
	}
}

func findAllEditorialLinks(html string, contestID int) []string {
	urls := make(map[string]bool)

	// 模式1: 明确的 Editorial 链接
	patterns := []string{
		`href="(/blog/entry/\d+)"[^>]*>.*?Editorial`,
		`href="(/blog/entry/\d+)"[^>]*>.*?Tutorial`,
		`href="([^"]*contest/(\d+)/editorial[^"]*)"`,
		`href="(/data/editorial/[^"]*)"`,
	}

	for _, pattern := range patterns {
		regex := regexp.MustCompile(pattern)
		matches := regex.FindAllStringSubmatch(html, -1)
		for _, match := range matches {
			if len(match) > 1 {
				url := match[1]
				if !strings.HasPrefix(url, "http") {
					url = "https://codeforces.com" + url
				}
				urls[url] = true
			}
		}
	}

	// 模式2: 侧边栏的 Contest materials
	materialsRegex := regexp.MustCompile(`<div class="roundbox sidebox sidebar-menu[^>]*>[\s\S]*?</div>\s*</div>`)
	materialsMatch := materialsRegex.FindStringSubmatch(html)
	if len(materialsMatch) > 0 {
		linkRegex := regexp.MustCompile(`href="([^"]*)"`)
		links := linkRegex.FindAllStringSubmatch(materialsMatch[0], -1)
		for _, link := range links {
			url := link[1]
			if strings.Contains(url, "blog/entry") || strings.Contains(url, "editorial") || strings.Contains(url, "Tutorial") {
				if !strings.HasPrefix(url, "http") {
					url = "https://codeforces.com" + url
				}
				urls[url] = true
			}
		}
	}

	// 模式3: 尝试常见的 editorial URL 格式
	commonURLs := []string{
		fmt.Sprintf("https://codeforces.com/blog/entry/%d", contestID),
		fmt.Sprintf("https://codeforces.com/contest/%d/editorial", contestID),
	}
	for _, url := range commonURLs {
		urls[url] = true
	}

	var result []string
	for url := range urls {
		result = append(result, url)
	}
	return result
}

func isRealTutorial(content string) bool {
	if len(content) < 500 {
		return false
	}

	// 检查是否包含题解关键词
	keywords := []string{
		"solution",
		"Solution",
		"complexity",
		"Complexity",
		"algorithm",
		"Algorithm",
		"approach",
		"Approach",
		"O(n)",
		"O(m)",
		"O(log",
		"DP",
		"greedy",
		"binary search",
	}

	keywordCount := 0
	for _, kw := range keywords {
		if strings.Contains(content, kw) {
			keywordCount++
		}
	}

	return keywordCount >= 3
}

func extractProblemSolutions(content string) map[string]string {
	solutions := make(map[string]string)

	// 尝试按题目分割
	// 格式1: "A. ..." 或 "Problem A"
	problemRegex := regexp.MustCompile(`(?i)(?:Problem\s+)?([A-Z])[\.\:]\s*`)
	
	// 找到所有题目标记的位置
	matches := problemRegex.FindAllStringSubmatchIndex(content, -1)
	
	for i, match := range matches {
		if len(match) >= 4 {
			problemID := content[match[2]:match[3]]
			start := match[1]
			end := len(content)
			if i+1 < len(matches) {
				end = matches[i+1][0]
			}
			solution := strings.TrimSpace(content[start:end])
			if len(solution) > 50 {
				solutions[problemID] = solution
			}
		}
	}

	return solutions
}

func extractTutorialContent(html string) string {
	// 方法1: 提取 ttypography 内容
	contentRegex := regexp.MustCompile(`<div class="ttypography">([\s\S]*?)</div>\s*</div>\s*</div>`)
	match := contentRegex.FindStringSubmatch(html)

	if len(match) > 1 {
		content := match[1]
		return cleanContent(content)
	}

	// 方法2: 提取 spoiler 内容
	spoilerRegex := regexp.MustCompile(`<div class="spoiler[^"]*"[^>]*>[\s\S]*?<div class="spoiler-content">([\s\S]*?)</div>`)
	matches := spoilerRegex.FindAllStringSubmatch(html, -1)

	var contents []string
	for _, m := range matches {
		if len(m) > 1 {
			contents = append(contents, cleanContent(m[1]))
		}
	}

	if len(contents) > 0 {
		return strings.Join(contents, "\n\n---\n\n")
	}

	return ""
}

func cleanContent(s string) string {
	// 移除脚本和样式
	s = regexp.MustCompile(`<script[^>]*>[\s\S]*?</script>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<style[^>]*>[\s\S]*?</style>`).ReplaceAllString(s, "")
	
	// 处理代码块
	s = regexp.MustCompile(`<pre[^>]*>`).ReplaceAllString(s, "\n```\n")
	s = regexp.MustCompile(`</pre>`).ReplaceAllString(s, "\n```\n")
	
	// 处理段落和换行
	s = regexp.MustCompile(`<p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`</p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<br\s*/?>`).ReplaceAllString(s, "\n")
	
	// 处理列表
	s = regexp.MustCompile(`<li>`).ReplaceAllString(s, "\n• ")
	s = regexp.MustCompile(`</li>`).ReplaceAllString(s, "")
	
	// 处理标题
	s = regexp.MustCompile(`<h[1-6][^>]*>`).ReplaceAllString(s, "\n## ")
	s = regexp.MustCompile(`</h[1-6]>`).ReplaceAllString(s, "\n")
	
	// 数学公式
	s = regexp.MustCompile(`\$\$\$`).ReplaceAllString(s, "$")
	
	// 移除其他标签
	s = regexp.MustCompile(`<[^>]+>`).ReplaceAllString(s, "")
	
	// 解码 HTML 实体
	s = decodeHTML(s)
	
	// 清理空白
	lines := strings.Split(s, "\n")
	var result []string
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" {
			result = append(result, line)
		}
	}
	
	return strings.Join(result, "\n")
}

func fetchHTML(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}

func decodeHTML(s string) string {
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", "\"")
	s = strings.ReplaceAll(s, "&#39;", "'")
	s = strings.ReplaceAll(s, "&nbsp;", " ")
	return s
}

func saveTutorial(contestID int, url, content string, problems map[string]string) {
	data := map[string]interface{}{
		"contest_id":       contestID,
		"url":              url,
		"content":          content,
		"problem_solutions": problems,
		"fetched_at":       time.Now().Format("2006-01-02 15:04:05"),
	}

	jsonData, _ := json.MarshalIndent(data, "", "  ")
	path := fmt.Sprintf("data/cf-problems/tutorials/tutorial_%d.json", contestID)
	os.WriteFile(path, jsonData, 0644)
	fmt.Printf("💾 已保存到: %s\n", path)
}