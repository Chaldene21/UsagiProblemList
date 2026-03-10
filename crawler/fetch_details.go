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

// ProblemDetail 表示题目详情
type ProblemDetail struct {
	ID          string   `json:"id"`
	ContestID   int      `json:"contest_id"`
	Index       string   `json:"index"`
	Name        string   `json:"name"`
	Difficulty  int      `json:"difficulty"`
	Tags        []string `json:"tags"`
	URL         string   `json:"url"`
	TimeLimit   string   `json:"time_limit"`
	MemoryLimit string   `json:"memory_limit"`
	Statement   string   `json:"statement"`
	Input       string   `json:"input"`
	Output      string   `json:"output"`
	Samples     []Sample `json:"samples"`
	Note        string   `json:"note"`
	Hints       []string `json:"hints"`
	Tutorial    string   `json:"tutorial"`
}

// Sample 表示样例
type Sample struct {
	Input  string `json:"input"`
	Output string `json:"output"`
}

// ProblemIndex 表示题目索引
type ProblemIndex struct {
	ID         string   `json:"id"`
	ContestID  int      `json:"contest_id"`
	Index      string   `json:"index"`
	Name       string   `json:"name"`
	Difficulty int      `json:"difficulty"`
	Tags       []string `json:"tags"`
	URL        string   `json:"url"`
}

// ProblemSetIndex 题目索引文件
type ProblemSetIndex struct {
	TotalProblems int            `json:"total_problems"`
	LastUpdated   string         `json:"last_updated"`
	Problems      []ProblemIndex `json:"problems"`
}

const (
	baseURL      = "https://codeforces.com/problemset/problem"
	tutorialURL  = "https://codeforces.com/blog/entry"
	outputDir    = "data/cf-problems"
	detailsDir   = "data/cf-problems/details"
	indexPath    = "data/cf-problems/problems.json"
	concurrency  = 10
	requestDelay = 200 * time.Millisecond
	maxRetries   = 3
	batchSize    = 0 // 0 表示不限制
)

var client *http.Client

func main() {
	fmt.Println("🐰 Codeforces 题目详情抓取器 v2.0")
	fmt.Println(strings.Repeat("=", 50))

	if err := os.MkdirAll(detailsDir, 0755); err != nil {
		fmt.Printf("❌ 创建目录失败: %v\n", err)
		return
	}

	// 创建支持连接复用的 HTTP 客户端
	client = &http.Client{
		Timeout: 30 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        50,
			MaxIdleConnsPerHost: 50,
			IdleConnTimeout:     60 * time.Second,
			MaxConnsPerHost:     20,
		},
	}

	indexData, err := os.ReadFile(indexPath)
	if err != nil {
		fmt.Printf("❌ 读取索引文件失败: %v\n", err)
		return
	}

	var problemSet ProblemSetIndex
	if err := json.Unmarshal(indexData, &problemSet); err != nil {
		fmt.Printf("❌ 解析索引文件失败: %v\n", err)
		return
	}

	fmt.Printf("📚 题库共 %d 道题目\n", len(problemSet.Problems))

	completed := make(map[string]bool)
	files, _ := os.ReadDir(detailsDir)
	for _, f := range files {
		if strings.HasSuffix(f.Name(), ".json") {
			completed[strings.TrimSuffix(f.Name(), ".json")] = true
		}
	}
	fmt.Printf("✅ 已抓取: %d 道\n", len(completed))

	var toFetch []ProblemIndex
	for _, p := range problemSet.Problems {
		if !completed[p.ID] {
			toFetch = append(toFetch, p)
		}
	}

	if len(toFetch) == 0 {
		fmt.Println("\n🎉 所有题目详情已抓取完成！")
		return
	}

	fmt.Printf("📥 待抓取: %d 道\n", len(toFetch))

	batchToFetch := toFetch
	if batchSize > 0 && len(toFetch) > batchSize {
		batchToFetch = toFetch[:batchSize]
		fmt.Printf("📦 本批次抓取: %d 道 (剩余 %d 道)\n", len(batchToFetch), len(toFetch)-len(batchToFetch))
	}

	fmt.Println("\n🚀 开始多线程抓取...")
	startTime := time.Now()

	var wg sync.WaitGroup
	semaphore := make(chan struct{}, concurrency)
	var successCount, failCount int
	var mu sync.Mutex

	for i, p := range batchToFetch {
		wg.Add(1)
		go func(p ProblemIndex, idx int) {
			defer wg.Done()
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			time.Sleep(requestDelay)

			detail, err := fetchProblemDetail(p)
			if err != nil {
				mu.Lock()
				failCount++
				if failCount <= 5 {
					fmt.Printf("❌ [%s] 失败: %v\n", p.ID, err)
				}
				mu.Unlock()
				return
			}

			if err := saveProblemDetail(detail); err != nil {
				mu.Lock()
				failCount++
				mu.Unlock()
				return
			}

			mu.Lock()
			successCount++
			if (successCount%100 == 0) || (idx+1 == len(batchToFetch)) {
				elapsed := time.Since(startTime).Seconds()
				rate := float64(successCount) / elapsed
				remaining := float64(len(toFetch)-successCount) / rate
				fmt.Printf("⏳ 进度: %d/%d | 成功: %d | 失败: %d | 速度: %.1f题/秒 | 预计剩余: %.0f秒\n",
					successCount+failCount, len(batchToFetch), successCount, failCount, rate, remaining)
			}
			mu.Unlock()
		}(p, i)
	}

	wg.Wait()

	elapsed := time.Since(startTime)
	fmt.Printf("\n✅ 抓取完成！耗时: %v\n", elapsed)
	fmt.Printf("   成功: %d | 失败: %d\n", successCount, failCount)

	files, _ = os.ReadDir(detailsDir)
	totalDone := len(files)
	fmt.Printf("📊 总进度: %d / %d (%.1f%%)\n", totalDone, len(problemSet.Problems),
		float64(totalDone)/float64(len(problemSet.Problems))*100)

	if totalDone < len(problemSet.Problems) {
		fmt.Println("\n💡 请再次运行继续抓取剩余题目")
	}
}

func fetchProblemDetail(p ProblemIndex) (*ProblemDetail, error) {
	url := fmt.Sprintf("%s/%d/%s", baseURL, p.ContestID, p.Index)

	var html string
	var err error

	for retry := 0; retry < maxRetries; retry++ {
		html, err = fetchHTML(url)
		if err == nil {
			break
		}
		time.Sleep(time.Second * time.Duration(retry+1))
	}

	if err != nil {
		return nil, err
	}

	detail := &ProblemDetail{
		ID:         p.ID,
		ContestID:  p.ContestID,
		Index:      p.Index,
		Name:       p.Name,
		Difficulty: p.Difficulty,
		Tags:       p.Tags,
		URL:        url,
	}

	parseProblemHTML(html, detail)
	
	// 尝试获取 tutorial
	fetchTutorial(detail)

	return detail, nil
}

func fetchHTML(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.5")
	req.Header.Set("Connection", "keep-alive")

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

func parseProblemHTML(html string, detail *ProblemDetail) {
	// 提取 problem-statement 内容
	psRegex := regexp.MustCompile(`<div class="problem-statement">([\s\S]*?)</div>\s*<p>\s*</p>`)
	psMatch := psRegex.FindStringSubmatch(html)

	var psContent string
	if len(psMatch) > 1 {
		psContent = psMatch[1]
	} else {
		psRegex2 := regexp.MustCompile(`<div class="ttypography"><div class="problem-statement">([\s\S]*?)</div>\s*<p>`)
		psMatch2 := psRegex2.FindStringSubmatch(html)
		if len(psMatch2) > 1 {
			psContent = psMatch2[1]
		}
	}

	if psContent == "" {
		return
	}

	// 提取标题
	titleRegex := regexp.MustCompile(`<div class="header">[\s\S]*?<div class="title">([^<]*\.?\s*[^<]+)</div>`)
	if match := titleRegex.FindStringSubmatch(psContent); len(match) > 1 {
		title := strings.TrimSpace(match[1])
		if idx := strings.Index(title, ". "); idx != -1 {
			title = strings.TrimSpace(title[idx+2:])
		}
		detail.Name = title
	}

	// 提取时间限制
	timeRegex := regexp.MustCompile(`<div class="time-limit">[\s\S]*?per test</div>([^<]+)</div>`)
	if match := timeRegex.FindStringSubmatch(psContent); len(match) > 1 {
		detail.TimeLimit = strings.TrimSpace(match[1])
	}

	// 提取内存限制
	memoryRegex := regexp.MustCompile(`<div class="memory-limit">[\s\S]*?per test</div>([^<]+)</div>`)
	if match := memoryRegex.FindStringSubmatch(psContent); len(match) > 1 {
		detail.MemoryLimit = strings.TrimSpace(match[1])
	}

	// 提取题目描述
	headerEnd := strings.Index(psContent, `</div></div>`)
	if headerEnd == -1 {
		headerEnd = strings.Index(psContent, `</div></div></div>`)
	}
	if headerEnd != -1 {
		afterHeader := psContent[headerEnd+10:]
		inputSpecIdx := strings.Index(afterHeader, `<div class="input-specification">`)
		sampleTestsIdx := strings.Index(afterHeader, `<div class="sample-tests">`)

		endIdx := inputSpecIdx
		if endIdx == -1 || (sampleTestsIdx != -1 && sampleTestsIdx < endIdx) {
			endIdx = sampleTestsIdx
		}

		if endIdx == -1 {
			endIdx = len(afterHeader)
		}

		statementHTML := afterHeader[:endIdx]
		statementHTML = regexp.MustCompile(`^<div>`).ReplaceAllString(statementHTML, "")
		statementHTML = regexp.MustCompile(`^</div>`).ReplaceAllString(statementHTML, "")
		detail.Statement = cleanHTMLContent(statementHTML)
		// 清理开头的多余字符
		detail.Statement = strings.TrimPrefix(detail.Statement, "v>")
		detail.Statement = strings.TrimPrefix(detail.Statement, "→")
		detail.Statement = strings.TrimSpace(detail.Statement)
	}

	// 提取输入说明
	inputStart := strings.Index(psContent, `<div class="input-specification">`)
	if inputStart != -1 {
		inputSection := psContent[inputStart:]
		outputStart := strings.Index(inputSection, `<div class="output-specification">`)
		sampleStart := strings.Index(inputSection, `<div class="sample-tests">`)

		inputEnd := outputStart
		if inputEnd == -1 || (sampleStart != -1 && sampleStart < inputEnd) {
			inputEnd = sampleStart
		}
		if inputEnd == -1 {
			inputEnd = len(inputSection)
		}

		inputHTML := inputSection[:inputEnd]
		inputHTML = regexp.MustCompile(`<div class="section-title">Input</div>`).ReplaceAllString(inputHTML, "")
		detail.Input = cleanHTMLContent(inputHTML)
	}

	// 提取输出说明
	outputStart := strings.Index(psContent, `<div class="output-specification">`)
	if outputStart != -1 {
		outputSection := psContent[outputStart:]
		sampleStart := strings.Index(outputSection, `<div class="sample-tests">`)

		outputEnd := sampleStart
		if outputEnd == -1 {
			outputEnd = len(outputSection)
		}

		outputHTML := outputSection[:outputEnd]
		outputHTML = regexp.MustCompile(`<div class="section-title">Output</div>`).ReplaceAllString(outputHTML, "")
		detail.Output = cleanHTMLContent(outputHTML)
	}

	// 提取样例
	detail.Samples = extractSamples(psContent)

	// 提取备注
	noteStart := strings.Index(psContent, `<div class="note">`)
	if noteStart != -1 {
		noteSection := psContent[noteStart:]
		noteEnd := findClosingDiv(noteSection, len(`<div class="note">`))
		if noteEnd > 0 {
			noteHTML := noteSection[len(`<div class="note">`):noteEnd]
			noteHTML = regexp.MustCompile(`<div class="section-title">Note</div>`).ReplaceAllString(noteHTML, "")
			detail.Note = cleanHTMLContent(noteHTML)
		}
	}

	// 提取 hints（提示）
	detail.Hints = extractHints(psContent)
}

// findClosingDiv 找到匹配的 </div>
func findClosingDiv(s string, startIdx int) int {
	depth := 1
	for i := startIdx; i < len(s); i++ {
		if strings.HasPrefix(s[i:], `<div`) {
			depth++
		} else if strings.HasPrefix(s[i:], `</div>`) {
			depth--
			if depth == 0 {
				return i
			}
		}
	}
	return -1
}

func extractHints(psContent string) []string {
	hints := []string{}

	// 查找所有 hint div
	hintRegex := regexp.MustCompile(`<div class="hint">([\s\S]*?)</div>`)
	matches := hintRegex.FindAllStringSubmatch(psContent, -1)

	for _, match := range matches {
		if len(match) > 1 {
			hint := cleanHTMLContent(match[1])
			if hint != "" {
				hints = append(hints, hint)
			}
		}
	}

	return hints
}

func fetchTutorial(detail *ProblemDetail) {
	// 从题目页面的侧边栏获取 tutorial 链接
	// Tutorial 通常在 blog/entry/{id} 下
	// 这个需要根据具体题目查找 tutorial 链接
	// 暂时留空，后续可以扩展
}

func extractSamples(psContent string) []Sample {
	samples := []Sample{}

	// 找到 sample-test 区域
	sampleTestRegex := regexp.MustCompile(`<div class="sample-test">([\s\S]*?)</div>\s*</div>\s*</div>`)
	sampleMatch := sampleTestRegex.FindStringSubmatch(psContent)

	var sampleBlock string
	if len(sampleMatch) > 1 {
		sampleBlock = sampleMatch[1]
	} else {
		stStart := strings.Index(psContent, `<div class="sample-test">`)
		if stStart == -1 {
			return samples
		}

		remaining := psContent[stStart:]
		endIdx := findClosingDiv(remaining, len(`<div class="sample-test">`))
		if endIdx > 0 {
			sampleBlock = remaining[:endIdx+6]
		} else {
			return samples
		}
	}

	// 提取所有 input
	inputRegex := regexp.MustCompile(`<div class="input">[\s\S]*?<pre[^>]*>([\s\S]*?)</pre>`)
	inputs := inputRegex.FindAllStringSubmatch(sampleBlock, -1)

	// 提取所有 output
	outputRegex := regexp.MustCompile(`<div class="output">[\s\S]*?<pre[^>]*>([\s\S]*?)</pre>`)
	outputs := outputRegex.FindAllStringSubmatch(sampleBlock, -1)

	for i := 0; i < len(inputs) && i < len(outputs); i++ {
		input := cleanPreContent(inputs[i][1])
		output := cleanPreContent(outputs[i][1])

		samples = append(samples, Sample{
			Input:  input,
			Output: output,
		})
	}

	return samples
}

func cleanPreContent(s string) string {
	s = regexp.MustCompile(`<div[^>]*class="test-example-line[^"]*"[^>]*>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</div>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<br\s*/?>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<[^>]+>`).ReplaceAllString(s, "")
	s = decodeHTML(s)
	s = strings.TrimSpace(s)
	return s
}

func cleanHTMLContent(s string) string {
	s = regexp.MustCompile(`<p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`</p>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<br\s*/?>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<li>`).ReplaceAllString(s, "\n• ")
	s = regexp.MustCompile(`</li>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<ul[^>]*>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`</ul>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`\$\$\$`).ReplaceAllString(s, "$")
	s = regexp.MustCompile(`<i>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</i>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<b>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</b>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<em>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</em>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<strong>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</strong>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<span[^>]*>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</span>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`<div[^>]*>`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`</div>`).ReplaceAllString(s, "\n")
	s = regexp.MustCompile(`<[^>]+>`).ReplaceAllString(s, "")
	s = decodeHTML(s)

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

func decodeHTML(s string) string {
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", "\"")
	s = strings.ReplaceAll(s, "&#39;", "'")
	s = strings.ReplaceAll(s, "&nbsp;", " ")
	s = strings.ReplaceAll(s, "&mdash;", "—")
	s = strings.ReplaceAll(s, "&ndash;", "–")
	s = strings.ReplaceAll(s, "&times;", "×")
	s = strings.ReplaceAll(s, "&le;", "≤")
	s = strings.ReplaceAll(s, "&ge;", "≥")
	return s
}

func saveProblemDetail(detail *ProblemDetail) error {
	path := fmt.Sprintf("%s/%s.json", detailsDir, detail.ID)
	data, err := json.MarshalIndent(detail, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}