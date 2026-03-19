#!/usr/bin/env python3
"""临时脚本：更新 make_problem_list.py"""

new_code = '''"""
CFLister - 题单生成器
使用 DeepSeek LLM 智能汇总与整理题目，生成符合格式的题目集JSON文件
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class DeepSeekClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    def chat(self, messages: List[Dict], model: str = "deepseek-chat", temperature: float = 0.7, max_tokens: int = 8000) -> Optional[str]:
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=self.headers,
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}, timeout=120)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API 请求失败: {e}")
            return None


CATEGORY_KNOWLEDGE_POINTS = {
    "data-structures": {"name": "数据结构", "knowledge_points": [
        {"title": "线段树/树状数组", "description": "区间查询与修改、单点更新、前缀和优化"},
        {"title": "并查集", "description": "连通性判断、集合合并、路径压缩"},
        {"title": "单调栈/单调队列", "description": "滑动窗口最值、单调性应用"},
        {"title": "堆/优先队列", "description": "TopK问题、合并有序序列"},
        {"title": "平衡树", "description": "Treap、Splay、AVL"},
        {"title": "字典树/Trie", "description": "字符串前缀匹配、异或最值"},
        {"title": "ST表", "description": "静态RMQ、区间最值查询"}
    ]},
    "graphs": {"name": "图论", "knowledge_points": [
        {"title": "最短路算法", "description": "Dijkstra、Bellman-Ford、SPFA、Floyd"},
        {"title": "最小生成树", "description": "Kruskal、Prim、次小生成树"},
        {"title": "Tarjan算法", "description": "强连通分量、割点、桥"},
        {"title": "树相关算法", "description": "LCA、树链剖分、树形DP"},
        {"title": "拓扑排序", "description": "DAG判定、拓扑序"},
        {"title": "二分图", "description": "二分图判定、最大匹配、匈牙利算法"},
        {"title": "网络流", "description": "最大流、最小割、费用流"},
        {"title": "DFS/BFS", "description": "连通性、Flood Fill、迷宫问题"}
    ]},
    "dp": {"name": "动态规划", "knowledge_points": [
        {"title": "线性DP", "description": "LIS、LCS、数字三角形"},
        {"title": "背包DP", "description": "01背包、完全背包、多重背包"},
        {"title": "区间DP", "description": "矩阵链乘法、石子合并"},
        {"title": "树形DP", "description": "树的直径、换根DP"},
        {"title": "状压DP", "description": "旅行商问题、棋盘问题"},
        {"title": "数位DP", "description": "数字统计、数位限制"},
        {"title": "概率/期望DP", "description": "期望值计算、概率转移"},
        {"title": "优化技巧", "description": "单调队列优化、斜率优化"}
    ]},
    "greedy": {"name": "贪心算法", "knowledge_points": [
        {"title": "排序贪心", "description": "区间调度、活动选择"},
        {"title": "区间问题", "description": "区间覆盖、区间选点、区间分组"},
        {"title": "构造贪心", "description": "按特定规则构造、字典序最值"},
        {"title": "反悔贪心", "description": "优先队列反悔、可撤销贪心"},
        {"title": "数学贪心", "description": "取模最优、整除最优"},
        {"title": "博弈贪心", "description": "取石子游戏、公平组合游戏"}
    ]},
    "binary-search": {"name": "二分查找", "knowledge_points": [
        {"title": "二分答案", "description": "最大化最小值、第K小问题"},
        {"title": "二分查找", "description": "有序数组查找、Lower/Upper Bound"},
        {"title": "三分查找", "description": "单峰函数极值"},
        {"title": "二分+贪心", "description": "二分答案后贪心判定"},
        {"title": "二分+DP", "description": "二分答案后DP判定"}
    ]},
    "math": {"name": "数学", "knowledge_points": [
        {"title": "数论基础", "description": "GCD、LCM、素数筛、质因数分解"},
        {"title": "同余与模运算", "description": "模运算性质、中国剩余定理"},
        {"title": "组合数学", "description": "排列组合、容斥原理、鸽巢原理"},
        {"title": "快速幂与矩阵", "description": "矩阵快速幂、矩阵加速递推"},
        {"title": "欧拉函数", "description": "欧拉定理、费马小定理"},
        {"title": "多项式与生成函数", "description": "FFT/NTT、卷积"},
        {"title": "线性代数", "description": "高斯消元、线性基"},
        {"title": "博弈论", "description": "SG函数、Nim游戏"}
    ]},
    "strings": {"name": "字符串", "knowledge_points": [
        {"title": "字符串哈希", "description": "Rolling Hash、双哈希"},
        {"title": "KMP与模式匹配", "description": "Next数组、模式匹配"},
        {"title": "字典树/Trie", "description": "多模式匹配、前缀统计"},
        {"title": "后缀数组/后缀自动机", "description": "SA、SAM、最长公共子串"},
        {"title": "AC自动机", "description": "多模式匹配、fail指针"},
        {"title": "回文串", "description": "Manacher算法、回文自动机"},
        {"title": "Z函数", "description": "Z算法、前缀函数"}
    ]},
    "constructive": {"name": "构造算法", "knowledge_points": [
        {"title": "奇偶构造", "description": "利用奇偶性质构造方案"},
        {"title": "顺序构造", "description": "按特定顺序排列元素"},
        {"title": "模拟构造", "description": "按规则逐步构造答案"},
        {"title": "逆向构造", "description": "从结果反推过程"},
        {"title": "网格构造", "description": "矩阵、棋盘类构造"},
        {"title": "数学构造", "description": "利用数学性质构造解"}
    ]}
}


class ProblemListGenerator:
    def __init__(self, api_key: str):
        self.client = DeepSeekClient(api_key)
        self.problems = []
        self.problem_details = {}
        
    def load_problems(self, problems_file: str = "problems.json", problem_set_dir: str = "problem_set"):
        if os.path.exists(problems_file):
            with open(problems_file, 'r', encoding='utf-8') as f:
                self.problems = json.load(f)
            print(f"加载了 {len(self.problems)} 道题目基本信息")
        if os.path.exists(problem_set_dir):
            for filename in os.listdir(problem_set_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(problem_set_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if data.get("tutorial") or data.get("codes"):
                            if data.get("id"):
                                self.problem_details[data["id"]] = data
                    except: pass
            print(f"加载了 {len(self.problem_details)} 道有题解/代码的题目详情")
        return len(self.problems), len(self.problem_details)
    
    def get_problem_basic_info(self, problem_id: str) -> Optional[Dict]:
        for p in self.problems:
            if f"{p.get('contestId')}{p.get('index')}" == problem_id:
                return p
        return None
    
    def get_problems_with_tutorials(self, tags: List[str] = None) -> List[Dict]:
        result = []
        for problem_id, detail in self.problem_details.items():
            basic_info = self.get_problem_basic_info(problem_id)
            if basic_info:
                if tags and not any(tag in basic_info.get("tags", []) for tag in tags):
                    continue
                result.append({"id": problem_id, "name": basic_info.get("name"), "difficulty": basic_info.get("rating"),
                              "tags": basic_info.get("tags", []), "url": basic_info.get("url"),
                              "tutorial": detail.get("tutorial", "")[:1000] if detail.get("tutorial") else ""})
        return result
    
    def _select_balanced_problems(self, problems: List[Dict], max_problems: int) -> List[Dict]:
        layers = {"入门级(800-1200)": [], "基础级(1201-1600)": [], "进阶级(1601-2000)": [], "困难题(2001-2500)": [], "挑战题(2501+)": []}
        for p in problems:
            d = p.get("difficulty") or 0
            if d <= 1200: layers["入门级(800-1200)"].append(p)
            elif d <= 1600: layers["基础级(1201-1600)"].append(p)
            elif d <= 2000: layers["进阶级(1601-2000)"].append(p)
            elif d <= 2500: layers["困难题(2001-2500)"].append(p)
            else: layers["挑战题(2501+)"].append(p)
        print("难度分布:")
        for n, ps in layers.items(): print(f"  {n}: {len(ps)} 道")
        selected, ratios = [], {"入门级(800-1200)": 0.15, "基础级(1201-1600)": 0.25, "进阶级(1601-2000)": 0.30, "困难题(2001-2500)": 0.20, "挑战题(2501+)": 0.10}
        for n, r in ratios.items():
            lp = layers[n]
            tc = int(max_problems * r)
            if len(lp) <= tc: selected.extend(lp)
            else:
                lp.sort(key=lambda x: x.get("difficulty") or 0)
                step = len(lp) / tc
                selected.extend([lp[int(i * step)] for i in range(tc)])
        selected.sort(key=lambda x: x.get("difficulty") or 0)
        return selected[:max_problems]
    
    def generate_problem_list(self, category: str, tags: List[str] = None, min_difficulty: int = 0,
                              max_difficulty: int = 4000, max_problems: int = 50, output_file: str = None) -> Optional[Dict]:
        filtered = [p for p in self.get_problems_with_tutorials(tags) if min_difficulty <= (p.get("difficulty") or 0) <= max_difficulty]
        selected = self._select_balanced_problems(filtered, max_problems)
        if not selected: print("没有找到符合条件的题目"); return None
        print(f"最终筛选出 {len(selected)} 道题目")
        
        ck = category.lower().replace("-", "").replace("_", "").replace(" ", "")
        kc = next((CATEGORY_KNOWLEDGE_POINTS[k] for k in CATEGORY_KNOWLEDGE_POINTS if k.replace("-", "") == ck), None)
        kp = "\\n\\n【知识点划分】：\\n" + "\\n".join([f"{i+1}. {x['title']}: {x['description']}" for i, x in enumerate(kc.get("knowledge_points", []))]) if kc else ""
        
        summary = [{"id": p["id"], "name": p["name"], "difficulty": p.get("difficulty"), "tags": p.get("tags", []), "url": p.get("url")} for p in selected]
        sys_prompt = f"""你是算法竞赛教练。生成结构化题单JSON。
格式: {{"id":"x","title":"标题","description":"描述","category":"分类","sections":[{{"title":"章节","content":[{{"type":"paragraph","text":"简介"}},{{"title":"子标题","code_template":"代码","idea":"思路","problems":[{{"id":"x","name":"名称","difficulty":1200,"tags":[],"url":"URL","note":"分析"}}]}}]}}]}}
要求: 1.难度分布:入门15%基础25%进阶30%困难20%挑战10% 2.按知识点划分章节 3.标题明确如线段树/最短路 4.包含代码和思路 5.只输出JSON{kp}"""
        user_prompt = f"分类:{category}\\n题目:{json.dumps(summary, ensure_ascii=False)}\\n生成题单JSON"
        
        print("正在调用 DeepSeek API...")
        resp = self.client.chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}], temperature=0.5, max_tokens=8000)
        if not resp: print("生成失败"); return None
        try:
            js = resp.split("```json")[1].split("```")[0] if "```json" in resp else (resp.split("```")[1].split("```")[0] if "```" in resp else resp)
            pl = json.loads(js.strip())
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f: json.dump(pl, f, ensure_ascii=False, indent=2)
                print(f"题单已保存到: {output_file}")
            return pl
        except Exception as e: print(f"解析失败: {e}"); return None
    
    def generate_multi_category_lists(self, categories: List[Dict], output_dir: str = "problem_lists") -> List[Dict]:
        os.makedirs(output_dir, exist_ok=True)
        results = []
        for c in categories:
            print(f"\\n{'='*60}\\n生成分类: {c['category']}\\n{'='*60}")
            r = self.generate_problem_list(category=c["category"], tags=c.get("tags"), min_difficulty=c.get("min_difficulty", 0),
                                          max_difficulty=c.get("max_difficulty", 4000), max_problems=c.get("max_problems", 50),
                                          output_file=os.path.join(output_dir, f"{c['category'].replace(' ', '-')}.json"))
            if r: results.append(r)
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="sk-281e934bcc544d2d88b7ba87037d2e00")
    parser.add_argument("--category")
    parser.add_argument("--tags", nargs="+")
    parser.add_argument("--min-diff", type=int, default=0)
    parser.add_argument("--max-diff", type=int, default=4000)
    parser.add_argument("--max-problems", type=int, default=50)
    parser.add_argument("--output", default="problem_list.json")
    parser.add_argument("--batch", action="store_true")
    args = parser.parse_args()
    
    g = ProblemListGenerator(args.api_key)
    g.load_problems()
    
    if args.batch:
        cats = [
            {"category": "greedy", "tags": ["greedy"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "dp", "tags": ["dp"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "binary-search", "tags": ["binary search"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "graphs", "tags": ["graphs", "dfs and similar", "bfs", "trees", "shortest paths"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "data-structures", "tags": ["data structures", "dsu"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "math", "tags": ["math", "number theory", "combinatorics"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "strings", "tags": ["strings", "hashing"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
            {"category": "constructive", "tags": ["constructive algorithms"], "min_difficulty": 800, "max_difficulty": 3500, "max_problems": 80},
        ]
        g.generate_multi_category_lists(cats, "problem_lists")
        return
    
    if not args.category: print("请指定 --category"); return
    g.generate_problem_list(category=args.category, tags=args.tags, min_difficulty=args.min_diff,
                           max_difficulty=args.max_diff, max_problems=args.max_problems, output_file=args.output)


if __name__ == "__main__":
    main()
'''

with open('make_problem_list.py', 'w', encoding='utf-8') as f:
    f.write(new_code)
print('make_problem_list.py 已更新成功！')