package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

type ContestTutorial struct {
	ContestID int               `json:"contest_id"`
	URL       string            `json:"url"`
	Content   string            `json:"content"`
	Problems  map[string]string `json:"problems"`
	FetchedAt string            `json:"fetched_at"`
}

var client *http.Client

func main() {
	fmt.Println("🐰 Codeforces 题解抓取器 v4.0")
	fmt.Println(strings.Repeat("=", 50))

	client = &http.Client{
		Timeout: 20 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     30 * time.Second,
		},
	}

	// 读取题目索引
	indexData, _ := os.ReadFile("data/cf-problems/problems.json")
	var problemSet struct {
		Problems []struct {
			ContestID int `json:"contest_id"`
		} `json:"problems"`
	}
	json.Unmarshal(indexData, &problemSet)

	// 统计比赛
	contests := make(map[int]bool)
	for _, p := range problemSet.Problems {
		contests[p.ContestID] = true
	}

	// 检查已完成
	completed := make(map[int]bool)
	tutorialDir := "data/cf-problems/tutorials"
	os.MkdirAll(tutorialDir, 0755)
	files, _ := os.ReadDir(tutorialDir)
	for _, f := range files {
		if strings.HasSuffix(f.Name(), ".json") {
			var cid int
			fmt.Sscanf(f.Name(), "tutorial_%d.json", &cid)
			if cid > 0 {
				completed[cid] = true
			}
		}
	}

	fmt.Printf("📚 总比赛: %d | 已完成: %d\n", len(contests), len(completed))

	// 待抓取列表
	var toFetch []int
	for cid := range contests {
		if !completed[cid] {
			toFetch = append(toFetch, cid)
		}
	}

	fmt.Printf("📥 待抓取: %d\n\n", len(toFetch))

	var wg sync.WaitGroup
	sem := make(chan struct{}, 8)
	var success, fail int
	var mu sync.Mutex
	start := time.Now()

	for _, cid := range toFetch {
		wg.Add(1)
		go func(contestID int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			time.Sleep(150 * time.Millisecond)

			tut, err := fetchTutorial(contestID)
			if err != nil || tut == nil {
				mu.Lock()
				fail++
				mu.Unlock()
				return
			}

			saveTutorial(tut)
			mu.Lock()
			success++
			if success%10 == 0 {
				fmt.Printf("⏳ 成功: %d | 失败: %d\n", success, fail)
			}
			mu.Unlock()
		}(cid)
	}

	wg.Wait()

	fmt.Printf("\n✅ 完成！耗时: %v\n成功: %d | 失败: %d\n", time.Since(start), success, fail)
	mergeTutorialsToDetails()
}

func fetchTutorial(contestID int) (*ContestTutorial, error) {
	// 方法1: 直接尝试 /contest/{id}/editorial
	url := fmt.Sprintf("https://codeforces.com/contest/%d/editorial", contestID)
	html, err := fetchHTML(url)
	if err == nil {
		content := extractContent(html)
		if content != "" && isTutorial(content) {
			return &ContestTutorial{
				ContestID: contestID,
				URL:       url,
				Content:   content,
				Problems:  extractProblems(content),
				FetchedAt: time.Now().Format("2006-01-02 15:04:05"),
			}, nil
		}
	}

	// 方法2: 从比赛页面查找 editorial 链接
	contestURL := fmt.Sprintf("https://codeforces.com/contest/%d", contestID)
	contestHTML, err := fetchHTML(contestURL)
	if err != nil {
		return nil, err
	}

	// 查找所有 blog/entry 链接
	blogRegex := regexp.MustCompile(`href="(/blog/entry/\d+)"`)
	matches := blogRegex.FindAllStringSubmatch(contestHTML, -1)
	
	for _, match := range matches {
		if len(match) > 1 {
			blogURL := "https://codeforces.com" + match[1]
			
			// 检查链接文字是否包含 Editorial/Tutorial
			linkRegex := regexp.MustCompile(fmt.Sprintf(`href="%s"[^>]*>([^<]*)`, match[1]))
			linkMatch := linkRegex.FindStringSubmatch(contestHTML)
			if len(linkMatch) > 1 {
				linkText := strings.ToLower(linkMatch[1])
				if strings.Contains(linkText, "editorial") || strings.Contains(linkText, "tutorial") || strings.Contains(linkText, "题解") {
					blogHTML, err := fetchHTML(blogURL)
					if err != nil {
						continue
					}
					content := extractContent(blogHTML)
					if content != "" && isTutorial(content) {
						return &ContestTutorial{
							ContestID: contestID,
							URL:       blogURL,
							Content:   content,
							Problems:  extractProblems(content),
							FetchedAt: time.Now().Format("2006-01-02 15:04:05"),
						}, nil
					}
				}
			}
		}
	}

	// 方法3: 检查侧边栏 "Contest materials" 区域
	materialsRegex := regexp.MustCompile(`<div class="roundbox sidebox[^"]*sidebar-menu[^"]*"[\s\S]*?</div>\s*</div>`)
	materialsMatch := materialsRegex.FindString(contestHTML)
	if materialsMatch != "" {
		// 查找其中的 blog 链接
		blogLinks := blogRegex.FindAllStringSubmatch(materialsMatch, -1)
		for _, m := range blogLinks {
			if len(m) > 1 {
				blogURL := "https://codeforces.com" + m[1]
				blogHTML, err := fetchHTML(blogURL)
				if err != nil {
					continue
				}
				content := extractContent(blogHTML)
				if content != "" && isTutorial(content) {
					return &ContestTutorial{
						ContestID: contestID,
						URL:       blogURL,
						Content:   content,
						Problems:  extractProblems(content),
						FetchedAt: time.Now().Format("2006-01-02 15:04:05"),
					}, nil
				}
			}
		}
	}

	return nil, fmt.Errorf("no tutorial found")
}

func fetchHTML(url string) (string, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	return string(body), nil
}

func extractContent(html string) string {
	re := regexp.MustCompile(`<div class="ttypography">([\s\S]*?)</div>\s*</div>\s*</div>`)
	m := re.FindStringSubmatch(html)
	if len(m) > 1 {
		return clean(m[1])
	}
	return ""
}

func isTutorial(s string) bool {
	if len(s) < 300 {
		return false
	}
	kw := []string{"solution", "Solution", "complexity", "Complexity", "O(n)", "O(m)", "DP", "greedy", "algorithm", "Algorithm"}
	cnt := 0
	for _, k := range kw {
		if strings.Contains(s, k) {
			cnt++
		}
	}
	return cnt >= 2
}

func extractProblems(content string) map[string]string {
	result := make(map[string]string)

	// 匹配: 2048A - Title 或 A. Title
	re := regexp.MustCompile(`(?:\d+)?([A-Z][1-2]?)\s*[-–—:.]\s*[^\n]+`)
	matches := re.FindAllStringSubmatchIndex(content, -1)

	for i, m := range matches {
		if len(m) < 4 {
			continue
		}
		idx := content[m[2]:m[3]]
		start := m[1]
		end := len(content)
		if i+1 < len(matches) {
			end = matches[i+1][0]
		}

		sol := strings.TrimSpace(content[start:end])
		if len(sol) > 100 {
			result[idx] = sol
		}
	}

	return result
}

func clean(s string) string {
	s = regexp.MustCompile(`<script[^>]*>[\s\S]*?</script>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<style[^>]*>[\s\S]*?</style>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<pre[^>]*>`).ReplaceAllString(s, "\n```\n")
	s = regexp.MustCompile(`</pre>`).ReplaceAllString(s, "\n```\n")
	s = regexp.MustCompile(`<p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`</p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<br\s*/?>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<li>`).ReplaceAllString(s, "\n• ")
	s = regexp.MustCompile(`</li>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<[^>]+>`).ReplaceAllString(s, "")
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", "\"")
	s = strings.ReplaceAll(s, "&nbsp;", " ")
	s = strings.ReplaceAll(s, "$$$", "$")
	return strings.TrimSpace(s)
}

func saveTutorial(t *ContestTutorial) error {
	path := fmt.Sprintf("data/cf-problems/tutorials/tutorial_%d.json", t.ContestID)
	data, _ := json.MarshalIndent(t, "", "  ")
	return os.WriteFile(path, data, 0644)
}

func mergeTutorialsToDetails() {
	fmt.Println("\n📝 合并题解到题目详情...")

	tutorialDir := "data/cf-problems/tutorials"
	detailsDir := "data/cf-problems/details"

	files, _ := os.ReadDir(tutorialDir)
	merged := 0

	for _, f := range files {
		if !strings.HasSuffix(f.Name(), ".json") {
			continue
		}

		var tut ContestTutorial
		data, err := os.ReadFile(fmt.Sprintf("%s/%s", tutorialDir, f.Name()))
		if err != nil {
			continue
		}
		if json.Unmarshal(data, &tut) != nil {
			continue
		}

		for idx, sol := range tut.Problems {
			problemID := fmt.Sprintf("%d%s", tut.ContestID, idx)
			detailPath := fmt.Sprintf("%s/%s.json", detailsDir, problemID)

			detailData, err := os.ReadFile(detailPath)
			if err != nil {
				continue
			}

			var detail map[string]interface{}
			if json.Unmarshal(detailData, &detail) != nil {
				continue
			}

			// 只在有实际题解内容时更新
			if sol != "" && len(sol) > 100 {
				detail["tutorial"] = sol
				detail["tutorial_url"] = tut.URL
				newData, _ := json.MarshalIndent(detail, "", "  ")
				os.WriteFile(detailPath, newData, 0644)
				merged++
			}
		}
	}

	fmt.Printf("✅ 已合并 %d 个题解\n", merged)
}