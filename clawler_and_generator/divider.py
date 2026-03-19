#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
题目分类程序 - 使用LLM对题目进行算法大类分类
"""

import os
import json
import requests
from pathlib import Path
import time
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# API配置
API_KEY = "sk-281e934bcc544d2d88b7ba87037d2e00"
API_URL = "https://api.deepseek.com/chat/completions"

# 分类类别及说明
CATEGORIES = {
    "data-structure": "数据结构【线段树、平衡树、前缀和、并查集、优先队列等】",
    "graph": "图论【最短路、tarjan、网络流、最小生成树等】",
    "dp": "动态规划【背包、状态压缩dp、树形dp等】",
    "greedy": "贪心【排序贪心、构造贪心、博弈贪心等】",
    "binary-search": "二分【二分答案、三分、二分查找等】",
    "math": "数学【数论、快速幂、博弈论等】",
    "string": "字符串",
    "constructive": "构造【模拟构造、顺序构造、逆向构造等】"
}

# 分类中文映射
CATEGORY_CN = {
    "data-structure": "数据结构",
    "graph": "图论",
    "dp": "动态规划",
    "greedy": "贪心",
    "binary-search": "二分",
    "math": "数学",
    "string": "字符串",
    "constructive": "构造"
}

def get_category_from_llm(problem_data: dict, max_retries: int = 3) -> str:
    """
    调用LLM对题目进行分类
    
    Args:
        problem_data: 题目数据字典
        max_retries: 最大重试次数
        
    Returns:
        分类结果字符串
    """
    problem_id = problem_data.get("id", "")
    name = problem_data.get("name", "")
    description = problem_data.get("description", "")
    tags = problem_data.get("tags", [])
    tutorial = problem_data.get("tutorial", "")
    codes = problem_data.get("codes", [])
    
    # 获取代码片段
    code_snippet = ""
    if codes and len(codes) > 0:
        code_snippet = codes[0].get("code", "")[:800]
    
    # 构建分类选项说明
    category_options = "\n".join([f"{k}: {v}" for k, v in CATEGORIES.items()])
    
    # 构建prompt
    prompt = f"""根据以下题目信息，分类到最合适的一个算法类别。

题目名称: {name}

题目描述: {description[:600]}

题目标签: {tags}

题解说明: {tutorial[:400] if tutorial else '无'}

参考代码: {code_snippet[:400] if code_snippet else '无'}

分类选项:
{category_options}

只输出类别名称(如data-structure/graph/dp/greedy/binary-search/math/string/constructive):"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 20,
        "temperature": 0.1
    }
    
    # 明确禁用代理
    proxies = {
        'http': None,
        'https': None,
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60, verify=False, proxies=proxies)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip().lower()
            
            # 解析返回的类别
            for cat in CATEGORIES.keys():
                if cat in content or cat.replace("-", "") in content:
                    return cat
            
            # 默认返回constructive作为fallback
            return "constructive"
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"API调用失败 ({problem_id})，{wait_time}秒后重试 ({attempt+1}/{max_retries}): {e}")
                time.sleep(wait_time)
            else:
                print(f"API调用失败 ({problem_id})，已达最大重试次数: {e}")
                return "constructive"
    
    return "constructive"


def process_problem(json_path: Path, output_base: Path) -> tuple:
    """
    处理单个题目文件
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
        
        problem_id = problem_data.get("id", json_path.stem)
        
        # 检查是否已有分类
        if "layer1_tag" in problem_data:
            category = problem_data["layer1_tag"]
            print(f"[跳过] {problem_id} 已分类为: {category}")
            return (problem_id, category)
        
        # 调用LLM进行分类
        category = get_category_from_llm(problem_data)
        
        # 添加layer1_tag
        problem_data["layer1_tag"] = category
        
        # 确保输出目录存在
        category_dir = output_base / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入新文件
        output_path = category_dir / json_path.name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(problem_data, f, ensure_ascii=False, indent=2)
        
        print(f"[完成] {problem_id} -> {category} ({CATEGORY_CN.get(category, category)})")
        return (problem_id, category)
        
    except Exception as e:
        print(f"[错误] 处理 {json_path.name} 失败: {e}")
        return (json_path.stem, None)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='题目分类程序')
    parser.add_argument('--test', type=int, default=0, help='测试模式：只处理前N个题目')
    parser.add_argument('--delay', type=float, default=0.5, help='API调用间隔时间(秒)')
    parser.add_argument('--start', type=int, default=0, help='从第N个题目开始处理')
    args = parser.parse_args()
    
    problem_set_dir = Path("D:/CODE/CFLister/problem_set")
    output_base = Path("D:/CODE/CFLister/tidy_problem_set")
    
    # 创建输出目录
    output_base.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES.keys():
        (output_base / cat).mkdir(parents=True, exist_ok=True)
    
    # 获取所有JSON文件
    json_files = sorted(list(problem_set_dir.glob("*.json")))
    total = len(json_files)
    print(f"共发现 {total} 个题目文件")
    
    # 统计信息
    stats = {cat: 0 for cat in CATEGORIES.keys()}
    stats["failed"] = 0
    processed = 0
    
    # 起始位置
    if args.start > 0:
        json_files = json_files[args.start:]
        print(f"从第 {args.start+1} 个题目开始")
    
    # 测试模式
    if args.test > 0:
        json_files = json_files[:args.test]
        print(f"测试模式：只处理前 {args.test} 个题目")
    
    # 处理每个文件
    for json_path in json_files:
        processed += 1
        print(f"\n[{processed}/{len(json_files)}] 处理: {json_path.name}")
        
        problem_id, category = process_problem(json_path, output_base)
        
        if category:
            stats[category] = stats.get(category, 0) + 1
        else:
            stats["failed"] += 1
        
        print(f"进度: {processed}/{len(json_files)} | 成功: {processed - stats['failed']} | 失败: {stats['failed']}")
        
        time.sleep(args.delay)
    
    # 打印统计
    print("\n" + "="*50)
    print("分类完成！统计结果：")
    print("="*50)
    for cat in CATEGORIES.keys():
        print(f"{CATEGORY_CN.get(cat, cat)}: {stats.get(cat, 0)} 题")
    print(f"失败: {stats['failed']} 题")
    print(f"总计: {len(json_files)} 题")


if __name__ == "__main__":
    main()