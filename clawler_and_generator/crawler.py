"""
CFLister - Codeforces Problemset Crawler
使用 Codeforces API 爬取题目数据
API 文档: https://codeforces.com/apiHelp
"""

import requests
import json
import time
import urllib3
import ssl
import os

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CodeforcesAPI:
    """Codeforces API 客户端"""
    
    BASE_URL = "https://codeforces.com/api"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        # 禁用代理
        self.session.proxies = {
            "http": None,
            "https": None,
        }
        self.session.trust_env = False
        
        # 禁用 SSL 验证
        self.verify_ssl = False
    
    def _request(self, method, params=None, retry=3):
        """发送 API 请求"""
        url = f"{self.BASE_URL}/{method}"
        
        for attempt in range(retry):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=30,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "OK":
                    return data.get("result")
                else:
                    print(f"API 错误: {data.get('comment', 'Unknown error')}")
                    return None
                    
            except requests.exceptions.SSLError as e:
                print(f"SSL 错误 (尝试 {attempt + 1}/{retry}): {e}")
                if attempt == 0:
                    print("尝试禁用 SSL 验证...")
                    self.verify_ssl = False
                time.sleep(1)
                
            except requests.RequestException as e:
                print(f"请求失败 (尝试 {attempt + 1}/{retry}): {e}")
                time.sleep(2)
        
        print("所有重试均失败")
        return None
    
    def get_problemset(self, tags=None, problemset_name=None):
        """
        获取题目列表
        
        参数:
            tags: 标签过滤 (可选)
            problemset_name: 题集名称 (可选)
        
        返回:
            problems: 题目列表
            statistics: 题目统计信息
        """
        params = {}
        if tags:
            params["tags"] = ";".join(tags) if isinstance(tags, list) else tags
        if problemset_name:
            params["problemsetName"] = problemset_name
        
        result = self._request("problemset.problems", params)
        if result:
            return result.get("problems", []), result.get("problemStatistics", [])
        return None, None
    
    def get_recent_status(self, count=100):
        """
        获取最近的提交状态
        
        参数:
            count: 返回的提交数量 (最大1000)
        
        返回:
            提交列表
        """
        return self._request("problemset.recentStatus", {"count": min(count, 1000)})
    
    def get_user_info(self, handles):
        """
        获取用户信息
        
        参数:
            handles: 用户名 (可以是列表或字符串)
        
        返回:
            用户信息列表
        """
        if isinstance(handles, list):
            handles = ";".join(handles)
        return self._request("user.info", {"handles": handles})


def fetch_all_problems():
    """获取所有 Codeforces 题目并保存"""
    api = CodeforcesAPI()
    
    print("正在从 Codeforces API 获取题目数据...")
    print("=" * 60)
    
    # 获取题目列表
    problems, statistics = api.get_problemset()
    
    if not problems:
        print("获取题目失败")
        return None
    
    print(f"成功获取 {len(problems)} 道题目")
    print(f"成功获取 {len(statistics)} 条统计信息")
    
    # 合并题目和统计信息
    stats_dict = {}
    for stat in statistics:
        key = (stat.get("contestId"), stat.get("index"))
        stats_dict[key] = stat
    
    problem_list = []
    for problem in problems:
        key = (problem.get("contestId"), problem.get("index"))
        stat = stats_dict.get(key, {})
        
        problem_data = {
            "contestId": problem.get("contestId"),
            "index": problem.get("index"),
            "name": problem.get("name"),
            "type": problem.get("type"),
            "rating": problem.get("rating"),
            "tags": problem.get("tags", []),
            "points": problem.get("points"),
            "solvedCount": stat.get("solvedCount"),
        }
        
        # 构建题目 URL
        if problem_data["contestId"]:
            problem_data["url"] = f"https://codeforces.com/problemset/problem/{problem_data['contestId']}/{problem_data['index']}"
        
        problem_list.append(problem_data)
    
    # 按 contestId 和 index 排序
    problem_list.sort(key=lambda x: (x.get("contestId") or 0, x.get("index") or ""))
    
    # 保存到 JSON 文件
    with open("problems.json", "w", encoding="utf-8") as f:
        json.dump(problem_list, f, ensure_ascii=False, indent=2)
    print(f"\n题目数据已保存到 problems.json")
    
    # 保存为 Markdown 格式
    save_as_markdown(problem_list)
    
    # 打印统计信息
    print_statistics(problem_list)
    
    return problem_list


def save_as_markdown(problems):
    """保存为 Markdown 格式"""
    with open("problems.md", "w", encoding="utf-8") as f:
        f.write("# Codeforces Problemset\n\n")
        f.write(f"共 {len(problems)} 道题目\n\n")
        f.write("| # | ID | 名称 | 难度 | 解决数 | 标签 |\n")
        f.write("|---|-----|------|------|--------|------|\n")
        
        for i, p in enumerate(problems, 1):
            contest_id = p.get("contestId", "")
            index = p.get("index", "")
            name = p.get("name", "")
            rating = p.get("rating", "N/A")
            solved = p.get("solvedCount", "N/A")
            tags = ", ".join(p.get("tags", [])[:3])  # 只显示前3个标签
            url = p.get("url", "")
            
            if url:
                f.write(f"| {i} | [{contest_id}{index}]({url}) | {name} | {rating} | {solved} | {tags} |\n")
            else:
                f.write(f"| {i} | {contest_id}{index} | {name} | {rating} | {solved} | {tags} |\n")
    
    print("Markdown 文件已保存到 problems.md")


def print_statistics(problems):
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("统计信息:")
    print("=" * 60)
    
    # 难度分布
    ratings = {}
    for p in problems:
        r = p.get("rating")
        if r:
            ratings[r] = ratings.get(r, 0) + 1
    
    if ratings:
        print("\n难度分布:")
        for rating in sorted(ratings.keys()):
            print(f"  {rating}: {ratings[rating]} 题")
    
    # 标签统计
    tags_count = {}
    for p in problems:
        for tag in p.get("tags", []):
            tags_count[tag] = tags_count.get(tag, 0) + 1
    
    if tags_count:
        print("\n热门标签 (前10):")
        sorted_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags[:10]:
            print(f"  {tag}: {count} 题")
    
    # 预览
    print("\n" + "=" * 60)
    print("题目预览 (前5道):")
    print("=" * 60)
    for p in problems[:5]:
        print(f"\nID: {p.get('contestId')}{p.get('index')}")
        print(f"名称: {p.get('name')}")
        print(f"难度: {p.get('rating', 'N/A')}")
        print(f"解决数: {p.get('solvedCount', 'N/A')}")
        print(f"标签: {', '.join(p.get('tags', []))}")
        print(f"链接: {p.get('url', 'N/A')}")


if __name__ == "__main__":
    fetch_all_problems()