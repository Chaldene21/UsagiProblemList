"""
CFLister - Codeforces Problem Detail Crawler
爬取题目详情页内容，包括题解tutorial和代码
"""

import cloudscraper
import json
import time
import urllib3
import os
import re
import sys
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 清除代理环境变量
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    if key in os.environ:
        del os.environ[key]


class ProblemDetailCrawler:
    """Codeforces 题目详情爬虫"""
    
    BASE_URL = "https://codeforces.com"
    
    def __init__(self):
        # 使用 cloudscraper 绕过 Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
            }
        )
        
        # 禁用代理
        self.scraper.proxies = {
            'http': None,
            'https': None,
        }
        self.scraper.trust_env = False
        
        # 启用 SSL 验证 (cloudscraper 需要)
        self.verify_ssl = True
        
        # 请求间隔（秒）
        self.delay = 1.0
        
        print("CloudScraper 初始化完成 (代理已禁用)")
    
    def _request(self, url: str, retry: int = 3) -> Optional[str]:
        """发送 HTTP 请求获取页面内容"""
        for attempt in range(retry):
            try:
                response = self.scraper.get(
                    url, 
                    timeout=30,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                return response.text
                
            except Exception as e:
                print(f"    请求失败 (尝试 {attempt + 1}/{retry}): {e}")
                time.sleep(2)
        
        print(f"    所有重试均失败: {url}")
        return None
    
    def parse_problem_page(self, html: str, problem_id: str) -> Dict:
        """解析题目详情页面"""
        soup = BeautifulSoup(html, 'html.parser')
        
        problem_data = {
            "id": problem_id,
            "description": "",
            "input_format": "",
            "output_format": "",
            "examples": [],
            "note": "",
            "time_limit": "",
            "memory_limit": "",
            "tutorial_url": None,
        }
        
        try:
            # 查找题目内容容器
            problem_statement = soup.find('div', class_='problem-statement')
            
            if not problem_statement:
                print(f"    未找到题目内容: {problem_id}")
                return problem_data
            
            # 提取时间限制和内存限制
            time_limit_div = problem_statement.find('div', class_='time-limit')
            if time_limit_div:
                problem_data["time_limit"] = time_limit_div.get_text(strip=True).replace('time limit per test', '').strip()
            
            memory_limit_div = problem_statement.find('div', class_='memory-limit')
            if memory_limit_div:
                problem_data["memory_limit"] = memory_limit_div.get_text(strip=True).replace('memory limit per test', '').strip()
            
            # 提取题目描述
            description_div = problem_statement.find('div', class_=None)
            if description_div:
                problem_data["description"] = self._clean_text(description_div.get_text(separator='\n', strip=True))
            
            # 提取输入输出格式和样例
            sections = problem_statement.find_all('div', class_='section-title')
            
            for section in sections:
                section_text = section.get_text(strip=True).lower()
                content_div = section.find_next_sibling('div')
                
                if not content_div:
                    continue
                
                if 'input' in section_text and 'sample' not in section_text:
                    problem_data["input_format"] = self._clean_text(content_div.get_text(separator='\n', strip=True))
                elif 'output' in section_text and 'sample' not in section_text:
                    problem_data["output_format"] = self._clean_text(content_div.get_text(separator='\n', strip=True))
                elif 'note' in section_text:
                    problem_data["note"] = self._clean_text(content_div.get_text(separator='\n', strip=True))
            
            # 提取样例
            sample_tests = problem_statement.find_all('div', class_='sample-tests')
            for sample_test in sample_tests:
                example = {}
                
                input_div = sample_test.find('div', class_='input')
                if input_div:
                    pre = input_div.find('pre')
                    if pre:
                        example["input"] = self._clean_text(pre.get_text(strip=True))
                
                output_div = sample_test.find('div', class_='output')
                if output_div:
                    pre = output_div.find('pre')
                    if pre:
                        example["output"] = self._clean_text(pre.get_text(strip=True))
                
                if example:
                    problem_data["examples"].append(example)
            
            # 查找 tutorial 链接
            tutorial_link = self._find_tutorial_link(soup, problem_id)
            if tutorial_link:
                problem_data["tutorial_url"] = tutorial_link
            
        except Exception as e:
            print(f"    解析题目 {problem_id} 时出错: {e}")
        
        return problem_data
    
    def _find_tutorial_link(self, soup: BeautifulSoup, problem_id: str) -> Optional[str]:
        """查找题解链接 - 改进版，支持更多链接格式"""
        try:
            links = soup.find_all('a', href=True)
            
            # 优先级1: 查找文本完全匹配的tutorial/editorial链接
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # 完全匹配 "tutorial", "editorial", "题解"
                if text in ['tutorial', 'editorial', '题解', 'solution']:
                    if href.startswith('/'):
                        return self.BASE_URL + href
                    elif href.startswith('http'):
                        return href
            
            # 优先级2: 查找包含 tutorial/editorial 的链接文本
            # 如 "Tutorial #1", "Editorial for Round", "tutorial for problem A"
            tutorial_candidates = []
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # 检查是否包含关键词
                if any(kw in text for kw in ['tutorial', 'editorial', '题解', 'solution']):
                    # 过滤掉一些明显不是题解的链接
                    if 'comment' not in text and 'reply' not in text:
                        tutorial_candidates.append((href, text, len(text)))  # 记录文本长度，优先选择短文本
            
            # 优先选择文本较短的链接（通常是主要的题解链接）
            if tutorial_candidates:
                tutorial_candidates.sort(key=lambda x: x[2])  # 按文本长度排序
                href = tutorial_candidates[0][0]
                if href.startswith('/'):
                    return self.BASE_URL + href
                elif href.startswith('http'):
                    return href
            
            # 优先级3: 查找href中包含tutorial/editorial的链接
            for link in links:
                href = link.get('href', '')
                if '/tutorial' in href or '/editorial' in href:
                    if href.startswith('/'):
                        return self.BASE_URL + href
                    elif href.startswith('http'):
                        return href
            
            # 优先级4: 查找blog链接（很多题解是blog格式）
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                # 查找可能是题解的blog链接
                if '/blog/' in href or 'blog/entry' in href:
                    # 检查链接文本是否暗示是题解
                    if any(kw in text for kw in ['tutorial', 'editorial', 'solution', '题解', 'round', 'contest']):
                        if href.startswith('/'):
                            return self.BASE_URL + href
                        elif href.startswith('http'):
                            return href
                        
        except Exception as e:
            print(f"    查找tutorial链接出错: {e}")
        
        return None
    
    def parse_tutorial_page(self, html: str, problem_index: str) -> Dict:
        """解析题解页面，提取指定题目的tutorial和code"""
        soup = BeautifulSoup(html, 'html.parser')
        
        tutorial_data = {
            "tutorial": "",
            "codes": []
        }
        
        try:
            # 查找题解内容区域
            # Codeforces 题解通常在 .ttypography 或 .tutorial-content 中
            content_div = soup.find('div', class_='ttypography')
            
            if not content_div:
                content_div = soup.find('div', class_='blog-content')
            
            if not content_div:
                # 尝试其他选择器
                content_div = soup.find('div', class_='entry-content')
            
            if not content_div:
                print(f"    未找到题解内容区域")
                return tutorial_data
            
            # 查找对应题目的section
            # 通常题目会有标题如 "A. Problem Name" 或 "Problem A"
            problem_section = self._find_problem_section(content_div, problem_index)
            
            if problem_section:
                # 提取tutorial文本
                tutorial_text = self._extract_tutorial_text(problem_section)
                tutorial_data["tutorial"] = tutorial_text
                
                # 提取代码块
                codes = self._extract_codes(problem_section)
                tutorial_data["codes"] = codes
            else:
                # 如果找不到特定题目section，尝试提取整个页面的内容
                print(f"    未找到题目 {problem_index} 的特定section，尝试提取整体内容")
                tutorial_text = self._extract_tutorial_text(content_div)
                tutorial_data["tutorial"] = tutorial_text
                codes = self._extract_codes(content_div)
                tutorial_data["codes"] = codes
                
        except Exception as e:
            print(f"    解析题解页面出错: {e}")
        
        return tutorial_data
    
    def _find_problem_section(self, content_div, problem_index: str) -> Optional[BeautifulSoup]:
        """在题解页面中查找对应题目的section"""
        try:
            problem_index_upper = problem_index.upper()
            
            # 策略1: 查找标题元素 (如 "1850A - To My Critics" 格式)
            headers = content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
            
            for i, header in enumerate(headers):
                text = header.get_text(strip=True)
                
                # 检查标题是否以题目编号开头 (如 "1850A -" 或 "A -")
                # 格式: "1850A - Problem Name" 或 "A. Problem Name"
                patterns = [
                    rf'^\d*{problem_index_upper}\s*[\.\-\:]',  # "1850A -" 或 "A."
                    rf'^{problem_index_upper}\s*[\.\-\:]',      # "A -" 或 "A."
                    rf'^Problem\s+{problem_index_upper}',
                    rf'^Solution\s+{problem_index_upper}',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        print(f"    找到题目标题: {text[:50]}...")
                        # 找到标题，提取该section的内容
                        return self._extract_section_after_header(header, content_div, problem_index_upper)
            
            # 策略2: 如果没找到标题，尝试通过查找solution collapse块
            # Codeforces 题解页面通常有折叠的solution块
            solution_divs = content_div.find_all('div', class_='spoiler')
            if solution_divs:
                # 返回整个content_div，但我们会尝试识别每个代码块对应的题目
                return content_div
                
            # 策略3: 返回整个内容区域
            return content_div
                
        except Exception as e:
            print(f"    查找题目section出错: {e}")
        
        return content_div
    
    def _extract_section_after_header(self, header, content_div, problem_index: str) -> BeautifulSoup:
        """提取header之后到下一个同级标题之间的内容"""
        from bs4 import Tag, NavigableString
        
        # 创建新的div来存储提取的内容
        new_div = BeautifulSoup('<div class="problem-section"></div>', 'html.parser').div
        
        current = header.next_sibling
        collected_text = []
        collected_codes = []
        
        while current:
            if isinstance(current, Tag):
                # 检查是否到了下一个题目标题
                if current.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    header_text = current.get_text(strip=True)
                    # 检查是否是另一道题目的标题 (以数字+字母开头)
                    if re.match(r'^\d*[A-Z]\s*[\.\-\:]', header_text):
                        break  # 到了下一题，停止
                
                # 收集代码块
                if current.name == 'pre':
                    code = current.find('code')
                    if code:
                        collected_codes.append(code.get_text())
                    else:
                        collected_codes.append(current.get_text())
                else:
                    # 递归查找代码块
                    for pre in current.find_all('pre'):
                        code = pre.find('code')
                        if code:
                            collected_codes.append(code.get_text())
                        else:
                            collected_codes.append(pre.get_text())
            
            current = current.next_sibling
        
        # 返回原始content_div（简化处理，实际内容由_extract_tutorial_text处理）
        return content_div
    
    def _get_section_content(self, start_element, content_div) -> BeautifulSoup:
        """获取从start_element开始到下一个同级标题之间的内容"""
        # 创建一个新的div来包含section内容
        from bs4 import Tag
        
        section_elements = []
        current = start_element.next_sibling
        
        # 收集元素直到遇到下一个同级别或更高级别的标题
        start_tag = start_element.name if isinstance(start_element, Tag) else None
        
        while current:
            if isinstance(current, Tag):
                # 如果遇到同级或更高级标题，停止
                if current.name in ['h1', 'h2', 'h3', 'h4']:
                    if start_tag and self._heading_level(current.name) <= self._heading_level(start_tag):
                        break
            section_elements.append(current)
            current = current.next_sibling
        
        # 返回原始content_div（简化处理）
        return content_div
    
    def _heading_level(self, tag_name: str) -> int:
        """获取标题级别"""
        levels = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4}
        return levels.get(tag_name, 5)
    
    def _extract_tutorial_text(self, content_div) -> str:
        """提取题解文本内容"""
        if not content_div:
            return ""
        
        try:
            # 移除代码块，只保留文本
            content_copy = BeautifulSoup(str(content_div), 'html.parser')
            
            # 移除pre和code标签（代码部分）
            for code_tag in content_copy.find_all(['pre', 'code']):
                code_tag.decompose()
            
            # 获取文本
            text = content_copy.get_text(separator='\n', strip=True)
            
            # 清理文本
            text = self._clean_text(text)
            
            # 限制长度
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            return text
            
        except Exception as e:
            print(f"    提取题解文本出错: {e}")
            return ""
    
    def _extract_codes(self, content_div) -> List[Dict]:
        """提取代码块"""
        codes = []
        
        if not content_div:
            return codes
        
        try:
            # 查找所有代码块
            pre_tags = content_div.find_all('pre')
            
            for pre in pre_tags:
                code_info = {}
                
                # 尝试识别语言
                code_tag = pre.find('code')
                if code_tag:
                    # 检查class来确定语言
                    classes = code_tag.get('class', [])
                    language = "unknown"
                    
                    for cls in classes:
                        if 'language-' in cls:
                            language = cls.replace('language-', '')
                            break
                        # 常见语言关键词
                        for lang in ['cpp', 'c++', 'python', 'java', 'c', 'pascal', 'delphi']:
                            if lang in cls.lower():
                                language = lang
                                break
                    
                    code_info["language"] = language
                    code_text = code_tag.get_text()
                else:
                    code_info["language"] = self._detect_language(pre.get_text())
                    code_text = pre.get_text()
                
                # 清理代码
                code_text = code_text.strip()
                if code_text and len(code_text) > 10:  # 过滤太短的代码
                    code_info["code"] = code_text
                    codes.append(code_info)
                    
                    # 限制代码数量
                    if len(codes) >= 5:
                        break
                        
        except Exception as e:
            print(f"    提取代码出错: {e}")
        
        return codes
    
    def _detect_language(self, code: str) -> str:
        """尝试检测代码语言"""
        code_lower = code.lower()
        
        # C++ 特征
        if any(kw in code_lower for kw in ['#include', 'iostream', 'vector', 'cout', 'cin', 'int main']):
            return 'cpp'
        
        # Python 特征
        if any(kw in code_lower for kw in ['def ', 'import ', 'print(', 'input(', 'if __name__']):
            return 'python'
        
        # Java 特征
        if any(kw in code_lower for kw in ['public class', 'public static', 'system.out', 'import java']):
            return 'java'
        
        # C 特征
        if '#include' in code_lower and 'iostream' not in code_lower:
            return 'c'
        
        return 'unknown'
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        # 移除多余的空白字符
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        return text
    
    def crawl_problem(self, contest_id: int, index: str, include_tutorial: bool = True) -> Optional[Dict]:
        """爬取单个题目详情"""
        # 构建 URL - problemset 页面
        url = f"{self.BASE_URL}/problemset/problem/{contest_id}/{index}"
        
        print(f"  正在爬取: {url}")
        
        html = self._request(url)
        if not html:
            # 尝试 contest 页面
            url = f"{self.BASE_URL}/contest/{contest_id}/problem/{index}"
            print(f"  尝试 contest URL: {url}")
            html = self._request(url)
        
        if not html:
            return None
        
        problem_id = f"{contest_id}{index}"
        problem_data = self.parse_problem_page(html, problem_id)
        
        # 爬取题解
        if include_tutorial and problem_data.get("tutorial_url"):
            print(f"  正在爬取题解: {problem_data['tutorial_url']}")
            tutorial_html = self._request(problem_data["tutorial_url"])
            
            if tutorial_html:
                tutorial_data = self.parse_tutorial_page(tutorial_html, index)
                problem_data["tutorial"] = tutorial_data.get("tutorial", "")
                problem_data["codes"] = tutorial_data.get("codes", [])
            else:
                problem_data["tutorial"] = ""
                problem_data["codes"] = []
        else:
            # 尝试直接构建tutorial URL
            if include_tutorial:
                tutorial_url = f"{self.BASE_URL}/contest/{contest_id}/tutorial"
                print(f"  尝试题解URL: {tutorial_url}")
                tutorial_html = self._request(tutorial_url)
                
                if tutorial_html:
                    tutorial_data = self.parse_tutorial_page(tutorial_html, index)
                    problem_data["tutorial"] = tutorial_data.get("tutorial", "")
                    problem_data["codes"] = tutorial_data.get("codes", [])
                    problem_data["tutorial_url"] = tutorial_url
                else:
                    problem_data["tutorial"] = ""
                    problem_data["codes"] = []
        
        # 请求间隔
        time.sleep(self.delay)
        
        return problem_data
    
    def crawl_all_problems(self, problems_file: str = "problems.json", output_dir: str = "problem_set", include_tutorial: bool = True):
        """爬取所有题目详情"""
        
        # 读取题目列表
        if not os.path.exists(problems_file):
            print(f"题目列表文件不存在: {problems_file}")
            return
        
        with open(problems_file, 'r', encoding='utf-8') as f:
            problems = json.load(f)
        
        print(f"共 {len(problems)} 道题目待爬取")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 统计
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, problem in enumerate(problems, 1):
            contest_id = problem.get("contestId")
            index = problem.get("index")
            
            if not contest_id or not index:
                print(f"跳过无效题目: {problem}")
                skip_count += 1
                continue
            
            problem_id = f"{contest_id}{index}"
            output_file = os.path.join(output_dir, f"{problem_id}.json")
            
            # 检查是否已存在且包含题解
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # 如果已有题解数据，跳过
                    if include_tutorial and existing_data.get("tutorial"):
                        print(f"[{i}/{len(problems)}] 已存在完整数据，跳过: {problem_id}")
                        skip_count += 1
                        continue
                    elif not include_tutorial and existing_data.get("description"):
                        print(f"[{i}/{len(problems)}] 已存在，跳过: {problem_id}")
                        skip_count += 1
                        continue
                except:
                    pass
            
            print(f"[{i}/{len(problems)}] 正在爬取: {problem_id} - {problem.get('name', '')}")
            
            # 爬取题目详情
            detail = self.crawl_problem(contest_id, index, include_tutorial)
            
            if detail:
                # 合并基本信息和详情
                full_data = {
                    "id": problem_id,
                    "contestId": contest_id,
                    "index": index,
                    "name": problem.get("name"),
                    "difficulty": problem.get("rating"),
                    "tags": problem.get("tags", []),
                    "url": problem.get("url"),
                    "solvedCount": problem.get("solvedCount"),
                    "time_limit": detail.get("time_limit"),
                    "memory_limit": detail.get("memory_limit"),
                    "description": detail.get("description"),
                    "input_format": detail.get("input_format"),
                    "output_format": detail.get("output_format"),
                    "examples": detail.get("examples"),
                    "note": detail.get("note"),
                    "tutorial_url": detail.get("tutorial_url"),
                    "tutorial": detail.get("tutorial", ""),
                    "codes": detail.get("codes", []),
                }
                
                # 保存到文件
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(full_data, f, ensure_ascii=False, indent=2)
                
                print(f"    -> 保存成功: {output_file}")
                success_count += 1
            else:
                print(f"    -> 爬取失败")
                fail_count += 1
        
        # 打印统计
        print("\n" + "=" * 60)
        print("爬取完成!")
        print("=" * 60)
        print(f"成功: {success_count}")
        print(f"失败: {fail_count}")
        print(f"跳过: {skip_count}")
        print(f"输出目录: {output_dir}")
    
    def update_existing_problems(self, output_dir: str = "problem_set"):
        """更新已存在的题目，添加题解和代码"""
        
        if not os.path.exists(output_dir):
            print(f"输出目录不存在: {output_dir}")
            return
        
        # 获取所有已存在的题目文件
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        
        print(f"共 {len(json_files)} 个已存在的题目文件")
        
        updated_count = 0
        skip_count = 0
        fail_count = 0
        
        for i, filename in enumerate(json_files, 1):
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否已有题解
                if data.get("tutorial"):
                    print(f"[{i}/{len(json_files)}] 已有题解，跳过: {filename}")
                    skip_count += 1
                    continue
                
                contest_id = data.get("contestId")
                index = data.get("index")
                
                if not contest_id or not index:
                    print(f"[{i}/{len(json_files)}] 无效数据，跳过: {filename}")
                    skip_count += 1
                    continue
                
                print(f"[{i}/{len(json_files)}] 更新题解: {filename}")
                
                # 尝试获取题解
                tutorial_url = f"https://codeforces.com/contest/{contest_id}/tutorial"
                tutorial_html = self._request(tutorial_url)
                
                if tutorial_html:
                    tutorial_data = self.parse_tutorial_page(tutorial_html, index)
                    data["tutorial"] = tutorial_data.get("tutorial", "")
                    data["codes"] = tutorial_data.get("codes", [])
                    data["tutorial_url"] = tutorial_url
                    
                    # 保存更新
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    print(f"    -> 更新成功")
                    updated_count += 1
                else:
                    print(f"    -> 获取题解失败")
                    fail_count += 1
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"[{i}/{len(json_files)}] 处理 {filename} 出错: {e}")
                fail_count += 1
        
        print("\n" + "=" * 60)
        print("更新完成!")
        print("=" * 60)
        print(f"更新成功: {updated_count}")
        print(f"跳过: {skip_count}")
        print(f"失败: {fail_count}")
    
    def fetch_tutorial_from_problem_page(self, contest_id: int, index: str) -> Optional[Dict]:
        """从题目详情页重新查找题解链接并爬取"""
        
        # 构建题目页面URL
        url = f"{self.BASE_URL}/problemset/problem/{contest_id}/{index}"
        
        print(f"  正在获取题目页面: {url}")
        
        html = self._request(url)
        if not html:
            # 尝试 contest 页面
            url = f"{self.BASE_URL}/contest/{contest_id}/problem/{index}"
            html = self._request(url)
        
        if not html:
            return None
        
        # 解析题目页面，查找tutorial链接
        soup = BeautifulSoup(html, 'html.parser')
        tutorial_url = self._find_tutorial_link(soup, f"{contest_id}{index}")
        
        if tutorial_url:
            print(f"  找到题解链接: {tutorial_url}")
            tutorial_html = self._request(tutorial_url)
            
            if tutorial_html:
                tutorial_data = self.parse_tutorial_page(tutorial_html, index)
                tutorial_data["tutorial_url"] = tutorial_url
                return tutorial_data
            else:
                print(f"  获取题解页面失败")
        else:
            # 尝试默认的tutorial URL
            tutorial_url = f"{self.BASE_URL}/contest/{contest_id}/tutorial"
            print(f"  未找到题解链接，尝试默认URL: {tutorial_url}")
            tutorial_html = self._request(tutorial_url)
            
            if tutorial_html:
                tutorial_data = self.parse_tutorial_page(tutorial_html, index)
                tutorial_data["tutorial_url"] = tutorial_url
                return tutorial_data
        
        return None
    
    def update_missing_tutorials(self, output_dir: str = "problem_set"):
        """更新缺失题解的题目 - 从题目详情页重新查找题解链接"""
        
        if not os.path.exists(output_dir):
            print(f"输出目录不存在: {output_dir}")
            return
        
        # 获取所有已存在的题目文件
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        
        print(f"共 {len(json_files)} 个已存在的题目文件")
        
        # 筛选缺失题解的题目
        missing_tutorial_files = []
        for filename in json_files:
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否缺失题解
                if not data.get("tutorial"):
                    missing_tutorial_files.append((filename, data))
            except:
                pass
        
        print(f"其中 {len(missing_tutorial_files)} 个题目缺失题解")
        
        if not missing_tutorial_files:
            print("所有题目都已有题解，无需更新")
            return
        
        updated_count = 0
        fail_count = 0
        
        for i, (filename, data) in enumerate(missing_tutorial_files, 1):
            filepath = os.path.join(output_dir, filename)
            
            contest_id = data.get("contestId")
            index = data.get("index")
            
            if not contest_id or not index:
                print(f"[{i}/{len(missing_tutorial_files)}] 无效数据，跳过: {filename}")
                fail_count += 1
                continue
            
            print(f"[{i}/{len(missing_tutorial_files)}] 更新题解: {filename} (Contest {contest_id}, Problem {index})")
            
            # 从题目详情页查找题解
            tutorial_data = self.fetch_tutorial_from_problem_page(contest_id, index)
            
            if tutorial_data and tutorial_data.get("tutorial"):
                data["tutorial"] = tutorial_data.get("tutorial", "")
                data["codes"] = tutorial_data.get("codes", [])
                data["tutorial_url"] = tutorial_data.get("tutorial_url")
                
                # 保存更新
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"    -> 更新成功")
                updated_count += 1
            else:
                print(f"    -> 未找到题解")
                fail_count += 1
            
            time.sleep(self.delay)
        
        print("\n" + "=" * 60)
        print("更新完成!")
        print("=" * 60)
        print(f"更新成功: {updated_count}")
        print(f"失败/未找到: {fail_count}")
    
    def crawl_by_tags(self, tags: List[str], problems_file: str = "problems.json", output_dir: str = "problem_set"):
        """按标签爬取题目"""
        
        # 读取题目列表
        if not os.path.exists(problems_file):
            print(f"题目列表文件不存在: {problems_file}")
            return
        
        with open(problems_file, 'r', encoding='utf-8') as f:
            problems = json.load(f)
        
        # 过滤指定标签的题目
        filtered_problems = []
        for problem in problems:
            problem_tags = problem.get("tags", [])
            if any(tag in problem_tags for tag in tags):
                filtered_problems.append(problem)
        
        print(f"找到 {len(filtered_problems)} 道包含标签 {tags} 的题目")
        
        # 创建临时文件
        temp_file = "temp_filtered_problems.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_problems, f, ensure_ascii=False, indent=2)
        
        # 爬取
        self.crawl_all_problems(temp_file, output_dir)
        
        # 删除临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Codeforces 题目详情爬虫")
    parser.add_argument("--all", action="store_true", help="爬取所有题目")
    parser.add_argument("--tags", nargs="+", help="按标签爬取 (如: --tags greedy dp)")
    parser.add_argument("--contest", type=int, help="爬取指定比赛的所有题目")
    parser.add_argument("--problem", type=str, help="爬取单个题目 (格式: 1A)")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔(秒)，默认1.0")
    parser.add_argument("--output", type=str, default="problem_set", help="输出目录")
    parser.add_argument("--no-tutorial", action="store_true", help="不爬取题解")
    parser.add_argument("--update", action="store_true", help="更新已存在的题目，添加题解")
    parser.add_argument("--update-missing", action="store_true", help="更新缺失题解的题目（从题目详情页重新查找题解链接）")
    
    args = parser.parse_args()
    
    crawler = ProblemDetailCrawler()
    crawler.delay = args.delay
    include_tutorial = not args.no_tutorial
    
    if args.update:
        # 更新模式：为已存在的题目添加题解
        crawler.update_existing_problems(args.output)
    
    elif args.update_missing:
        # 更新缺失题解的题目
        crawler.update_missing_tutorials(args.output)
    
    elif args.problem:
        # 爬取单个题目
        match = re.match(r'(\d+)([A-Za-z]+)', args.problem)
        if match:
            contest_id = int(match.group(1))
            index = match.group(2).upper()
            detail = crawler.crawl_problem(contest_id, index, include_tutorial)
            if detail:
                print(json.dumps(detail, ensure_ascii=False, indent=2))
            else:
                print("爬取失败")
        else:
            print("题目格式错误，正确格式如: 1A, 123B")
    
    elif args.contest:
        # 爬取指定比赛
        problems = []
        if os.path.exists("problems.json"):
            with open("problems.json", 'r', encoding='utf-8') as f:
                all_problems = json.load(f)
            problems = [p for p in all_problems if p.get("contestId") == args.contest]
        
        if problems:
            temp_file = "temp_contest_problems.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(problems, f, ensure_ascii=False, indent=2)
            crawler.crawl_all_problems(temp_file, args.output, include_tutorial)
            os.remove(temp_file)
        else:
            print(f"未找到比赛 {args.contest} 的题目")
    
    elif args.tags:
        # 按标签爬取
        crawler.crawl_by_tags(args.tags, "problems.json", args.output)
    
    elif args.all:
        # 爬取所有
        crawler.crawl_all_problems("problems.json", args.output, include_tutorial)
    
    else:
        # 默认显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()