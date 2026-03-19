"""
题目题单整合程序 - Reformer & Combiner
将零散的JSON整合成为几个大的题单JSON
"""

import os
import json
import shutil
import asyncio
import aiohttp
from typing import List, Dict, Any
from pathlib import Path
import re

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-281e934bcc544d2d88b7ba87037d2e00"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 目录配置
TIDY_PROBLEM_SET_DIR = "tidy_problem_set"
SET_FOR_LIST_DIR = "set_for_list"
PROBLEM_LISTS_DIR = "problem_lists"

# 并发配置
MAX_CONCURRENT_REQUESTS = 200


class ReformerCombiner:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_deepseek_api(self, messages: List[Dict], max_tokens: int = 2000) -> str:
        """调用DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            async with self.session.post(DEEPSEEK_API_URL, headers=headers, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API调用失败: {e}")
            return ""
    
    def copy_file_structure(self):
        """复制文件结构并重组"""
        print("步骤1: 复制文件结构并重组...")
        
        # 检查set_for_list目录是否已存在
        if os.path.exists(SET_FOR_LIST_DIR):
            print("检测到set_for_list目录已存在，跳过文件复制步骤（断点续传模式）")
            return
        
        # 创建set_for_list目录
        os.makedirs(SET_FOR_LIST_DIR, exist_ok=True)
        
        # 遍历tidy_problem_set
        for layer1_dir in os.listdir(TIDY_PROBLEM_SET_DIR):
            layer1_path = os.path.join(TIDY_PROBLEM_SET_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            # 创建layer1目录
            layer1_dest = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            os.makedirs(layer1_dest, exist_ok=True)
            
            # 遍历layer2
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                layer2_dest = os.path.join(layer1_dest, layer2_dir)
                os.makedirs(layer2_dest, exist_ok=True)
                
                # 处理layer2下的文件和子目录
                self._process_layer2_directory(layer2_path, layer2_dest, layer1_dir, layer2_dir)
        
        print("文件结构复制完成！")
    
    def _process_layer2_directory(self, src_dir: str, dest_dir: str, layer1_tag: str, layer2_tag: str):
        """处理layer2目录，合并深层文件夹到layer3层级"""
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            
            if os.path.isfile(src_path) and src_path.endswith('.json'):
                # 如果是JSON文件，读取检查是否有layer3_tag
                with open(src_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'layer3_tag' in data and data['layer3_tag']:
                    layer3_tag = data['layer3_tag']
                    layer3_dest = os.path.join(dest_dir, layer3_tag)
                    os.makedirs(layer3_dest, exist_ok=True)
                    
                    # 复制文件到layer3目录
                    dest_file = os.path.join(layer3_dest, os.path.basename(src_path))
                    shutil.copy2(src_path, dest_file)
                else:
                    # 如果没有layer3_tag，直接复制到layer2目录
                    shutil.copy2(src_path, dest_dir)
            
            elif os.path.isdir(src_path):
                # 如果是目录，检查是否是layer3_tag目录
                layer3_dest = os.path.join(dest_dir, item)
                os.makedirs(layer3_dest, exist_ok=True)
                
                # 递归处理该目录下的所有JSON文件
                self._flatten_directory(src_path, layer3_dest, layer1_tag, layer2_tag, item)
    
    def _flatten_directory(self, src_dir: str, dest_dir: str, layer1_tag: str, layer2_tag: str, layer3_tag: str):
        """扁平化深层目录，将所有JSON文件复制到layer3层级"""
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.json'):
                    src_file = os.path.join(root, file)
                    
                    # 读取JSON文件并添加layer_tag信息
                    with open(src_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 确保layer_tag信息存在
                    data['layer1_tag'] = layer1_tag
                    data['layer2_tag'] = layer2_tag
                    data['layer3_tag'] = layer3_tag
                    
                    # 保存到layer3目录
                    dest_file = os.path.join(dest_dir, file)
                    with open(dest_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def generate_solve_and_idea(self):
        """为每个layer3_tag目录生成solve_and_idea.json"""
        print("步骤2: 生成solve_and_idea.json文件...")
        
        skip_count = 0
        generate_count = 0
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                for layer3_dir in os.listdir(layer2_path):
                    layer3_path = os.path.join(layer2_path, layer3_dir)
                    if not os.path.isdir(layer3_path):
                        continue
                    
                    # 检查solve_and_idea.json是否已存在
                    solve_idea_path = os.path.join(layer3_path, "solve_and_idea.json")
                    if os.path.exists(solve_idea_path):
                        skip_count += 1
                        continue
                    
                    # 获取该目录下所有的JSON文件
                    json_files = [f for f in os.listdir(layer3_path) if f.endswith('.json') and f != 'solve_and_idea.json']
                    
                    if not json_files:
                        continue
                    
                    # 按batch处理（每30题）
                    batch_size = 30
                    for i in range(0, len(json_files), batch_size):
                        batch_files = json_files[i:i + batch_size]
                        await self._generate_solve_and_idea_for_batch(layer3_path, layer3_dir, batch_files)
                        generate_count += 1
        
        print(f"solve_and_idea.json生成完成！跳过 {skip_count} 个已存在的文件，新生成 {generate_count} 个文件")
    
    async def _generate_solve_and_idea_for_batch(self, layer3_path: str, layer3_tag: str, batch_files: List[str]):
        """为一个batch的题目生成solve_and_idea.json"""
        # 收集题目信息
        problems_info = []
        for filename in batch_files:
            filepath = os.path.join(layer3_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            problem_info = {
                'description': data.get('description', ''),
                'tags': data.get('tags', []),
                'tutorial': data.get('tutorial', ''),
                'code': data.get('codes', [])
            }
            problems_info.append(problem_info)
        
        # 构建prompt
        prompt = f"""你是一个算法竞赛题目的专家。我需要你为以下一组题目（共{len(problems_info)}题）生成一个通用的解题思路和代码模板。

这些题目都属于类别：{layer3_tag}

以下是题目的简要信息：
"""
        for idx, info in enumerate(problems_info, 1):
            prompt += f"\n题目{idx}:\n"
            prompt += f"描述: {info['description'][:200]}...\n"
            prompt += f"标签: {', '.join(info['tags'])}\n"
            if info['tutorial']:
                prompt += f"解题思路: {info['tutorial'][:200]}...\n"
        
        prompt += f"""

请根据这些题目的共同特点，生成一个JSON格式的回复，包含：
1. title: 子章节标题，与{layer3_tag}一致（格式：§{layer3_tag}）
2. code_template: 该类型题目的共性解法的框架性代码模板描述
3. idea: 该类型题目的解题思路描述

请只返回JSON，不要其他内容。"""

        # 调用API
        messages = [
            {"role": "system", "content": "你是一个算法竞赛专家，擅长总结题目规律和生成解题模板。"},
            {"role": "user", "content": prompt}
        ]
        
        result = await self.call_deepseek_api(messages)
        
        # 解析结果
        try:
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                solve_idea = json.loads(json_match.group())
            else:
                # 如果无法解析，使用默认模板
                solve_idea = {
                    "title": f"§{layer3_tag}",
                    "code_template": "// 请根据具体题目要求实现\n",
                    "idea": f"这是关于{layer3_tag}的题目"
                }
            
            # 保存到文件
            solve_idea_path = os.path.join(layer3_path, "solve_and_idea.json")
            with open(solve_idea_path, 'w', encoding='utf-8') as f:
                json.dump(solve_idea, f, ensure_ascii=False, indent=2)
            
            print(f"已生成 {layer3_path}/solve_and_idea.json")
            
        except Exception as e:
            print(f"生成solve_and_idea.json失败 {layer3_path}: {e}")
    
    async def rewrite_problem_jsons(self):
        """并发改写题目JSON文件"""
        print("步骤3: 改写题目JSON文件...")
        
        tasks = []
        skip_count = 0
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                for layer3_dir in os.listdir(layer2_path):
                    layer3_path = os.path.join(layer2_path, layer3_dir)
                    if not os.path.isdir(layer3_path):
                        continue
                    
                    # 读取solve_and_idea.json
                    solve_idea_path = os.path.join(layer3_path, "solve_and_idea.json")
                    if not os.path.exists(solve_idea_path):
                        continue
                    
                    with open(solve_idea_path, 'r', encoding='utf-8') as f:
                        solve_idea = json.load(f)
                    
                    # 获取所有题目JSON文件
                    json_files = [f for f in os.listdir(layer3_path) if f.endswith('.json') and f != 'solve_and_idea.json']
                    
                    for json_file in json_files:
                        json_path = os.path.join(layer3_path, json_file)
                        
                        # 检查文件是否已经被改写过
                        if self._is_rewritten(json_path):
                            skip_count += 1
                            continue
                        
                        tasks.append(self._rewrite_single_problem(json_path, solve_idea))
        
        if not tasks and skip_count > 0:
            print(f"所有题目JSON已经改写完成！跳过 {skip_count} 个已改写的文件")
            return
        
        # 并发执行，限制最大并发数
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[run_with_semaphore(task) for task in tasks])
        
        print(f"题目JSON改写完成！共处理 {len(results)} 个文件，跳过 {skip_count} 个已改写的文件")
    
    def _is_rewritten(self, json_path: str) -> bool:
        """检查JSON文件是否已经被改写过"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否包含改写后的必需字段
            required_fields = ['id', 'name', 'difficulty', 'tags', 'url', 'note']
            return all(field in data for field in required_fields)
        except:
            return False
    
    async def _rewrite_single_problem(self, json_path: str, solve_idea: Dict):
        """改写单个题目JSON"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 保留所有layer_tag信息
            layer_tags = {k: v for k, v in data.items() if k.startswith('layer')}
            
            # 构建prompt
            prompt = f"""你是一个算法竞赛专家。请为以下题目生成一个简洁的解题分析。

题目名称: {data.get('name', '')}
题目描述: {data.get('description', '')[:500]}...
标签: {', '.join(data.get('tags', []))}
解题思路: {data.get('tutorial', '')[:300]}...

该类型题目的通用解题思路是: {solve_idea.get('idea', '')}

请结合题目的描述、tutorial和题解代码，综合简明扼要地解释如何使用上述解题思路来解题。
要求：
1. 分析要简明扼要（50-100字）
2. 说明如何应用该类型的解题思路
3. 突出题目的关键点

请只返回分析文本，不要其他内容。"""
            
            # 调用API
            messages = [
                {"role": "system", "content": "你是一个算法竞赛专家，擅长分析题目和解题思路。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek_api(messages, max_tokens=300)
            
            # 构建新的JSON结构
            new_data = {
                **layer_tags,  # 保留所有layer_tag
                "id": data.get('id', ''),
                "name": data.get('name', ''),
                "difficulty": data.get('difficulty', 0),
                "tags": data.get('tags', []),
                "url": data.get('url', ''),
                "note": result.strip() if result else ""
            }
            
            # 保存文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"改写失败 {json_path}: {e}")
    
    async def combine_layer3_lists(self):
        """组合layer3题单"""
        print("步骤4: 生成layer3题单JSON...")
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                for layer3_dir in os.listdir(layer2_path):
                    layer3_path = os.path.join(layer2_path, layer3_dir)
                    if not os.path.isdir(layer3_path):
                        continue
                    
                    # 读取solve_and_idea.json
                    solve_idea_path = os.path.join(layer3_path, "solve_and_idea.json")
                    if not os.path.exists(solve_idea_path):
                        continue
                    
                    with open(solve_idea_path, 'r', encoding='utf-8') as f:
                        solve_idea = json.load(f)
                    
                    # 读取所有题目JSON
                    json_files = [f for f in os.listdir(layer3_path) if f.endswith('.json') and f != 'solve_and_idea.json']
                    problems = []
                    
                    for json_file in json_files:
                        json_path = os.path.join(layer3_path, json_file)
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        problems.append(data)
                    
                    if not problems:
                        continue
                    
                    # 分离有difficulty和没有difficulty的题目
                    problems_with_difficulty = [p for p in problems if p.get('difficulty') is not None]
                    problems_without_difficulty = [p for p in problems if p.get('difficulty') is None]
                    
                    # 如果全部题目都没有difficulty，跳过
                    if not problems_with_difficulty and not problems_without_difficulty:
                        continue
                    
                    # 对有difficulty的题目按难度升序排序
                    if problems_with_difficulty:
                        problems_with_difficulty.sort(key=lambda x: x.get('difficulty', 0))
                    
                    # 合并：有difficulty的在前，没有difficulty的在后
                    final_problems = problems_with_difficulty + problems_without_difficulty
                    
                    # 获取layer_tag信息（从第一个有效题目获取）
                    if final_problems:
                        first_problem = final_problems[0]
                    else:
                        continue
                    
                    # 构建layer3题单
                    layer3_list = {
                        "layer1_tag": first_problem.get('layer1_tag', ''),
                        "layer2_tag": first_problem.get('layer2_tag', ''),
                        "layer3_tag": layer3_dir,
                        "title": solve_idea.get('title', f"§{layer3_dir}"),
                        "code_template": solve_idea.get('code_template', ''),
                        "idea": solve_idea.get('idea', ''),
                        "problems": final_problems
                    }
                    
                    # 保存文件
                    output_path = os.path.join(layer3_path, f"{layer3_dir}.json")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(layer3_list, f, ensure_ascii=False, indent=2)
                    
                    print(f"已生成 {output_path}")
        
        print("layer3题单生成完成！")
    
    async def combine_layer2_lists(self):
        """组合layer2题单"""
        print("步骤5: 生成layer2题单JSON...")
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                # 收集所有layer3题单
                layer3_lists = []
                layer3_titles = []
                
                for layer3_dir in os.listdir(layer2_path):
                    layer3_path = os.path.join(layer2_path, layer3_dir)
                    if not os.path.isdir(layer3_path):
                        continue
                    
                    layer3_list_file = os.path.join(layer3_path, f"{layer3_dir}.json")
                    if not os.path.exists(layer3_list_file):
                        continue
                    
                    with open(layer3_list_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    layer3_lists.append(data)
                    layer3_titles.append(f"§{layer3_dir}")
                
                if not layer3_lists:
                    continue
                
                # 构建prompt获取text
                prompt = f"""你是一个算法竞赛专家。请为以下题单章节生成一个概要描述。

章节名称: {layer2_dir}
子章节包括: {', '.join(layer3_titles[:5])}{'...' if len(layer3_titles) > 5 else ''}

请生成一个简洁的章节概要（text），说明该章节包含哪些类型的题目及其特点。
要求：
1. 描述要简洁（100-200字）
2. 概括该章节的主要内容和特点
3. 说明可以解决哪些类型的问题

请只返回概要文本，不要其他内容。"""
                
                messages = [
                    {"role": "system", "content": "你是一个算法竞赛专家，擅长总结题目规律。"},
                    {"role": "user", "content": prompt}
                ]
                
                text_result = await self.call_deepseek_api(messages, max_tokens=300)
                
                # 构建layer2题单
                content_list = []
                for layer3_list in layer3_lists:
                    content_item = {
                        "title": layer3_list.get('title', ''),
                        "code_template": layer3_list.get('code_template', ''),
                        "idea": layer3_list.get('idea', ''),
                        "problems": layer3_list.get('problems', [])
                    }
                    content_list.append(content_item)
                
                layer2_list = {
                    "layer1_tag": layer1_dir,
                    "layer2_tag": layer2_dir,
                    "title": layer2_dir,
                    "text": text_result.strip() if text_result else "",
                    "content": content_list
                }
                
                # 保存文件
                output_path = os.path.join(layer2_path, f"{layer2_dir}.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(layer2_list, f, ensure_ascii=False, indent=2)
                
                print(f"已生成 {output_path}")
        
        print("layer2题单生成完成！")
    
    async def combine_layer1_lists(self):
        """组合layer1题单"""
        print("步骤6: 生成layer1题单JSON...")
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            # 收集所有layer2题单
            layer2_lists = []
            layer2_titles = []
            
            for layer2_dir in os.listdir(layer1_path):
                layer2_path = os.path.join(layer1_path, layer2_dir)
                if not os.path.isdir(layer2_path):
                    continue
                
                layer2_list_file = os.path.join(layer2_path, f"{layer2_dir}.json")
                if not os.path.exists(layer2_list_file):
                    continue
                
                with open(layer2_list_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                layer2_lists.append(data)
                layer2_titles.append(data.get('title', layer2_dir))
            
            if not layer2_lists:
                continue
            
            # 构建prompt获取description
            prompt = f"""你是一个算法竞赛专家。请为以下题单生成一个描述。

题单名称: {layer1_dir}
章节包括: {', '.join(layer2_titles[:3])}{'...' if len(layer2_titles) > 3 else ''}

请生成：
1. id: 题单唯一标识（格式：{layer1_dir}-101）
2. title: 题单标题（中文名称，与{layer1_dir}相关）
3. description: 对于该题单的描述（150-300字）
4. category: 该题单的分类标签

请以JSON格式返回，包含以上4个字段。"""
            
            messages = [
                {"role": "system", "content": "你是一个算法竞赛专家，擅长总结题单。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek_api(messages, max_tokens=500)
            
            # 解析结果
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    meta_info = json.loads(json_match.group())
                else:
                    meta_info = {
                        "id": f"{layer1_dir}-101",
                        "title": layer1_dir,
                        "description": f"这是一个关于{layer1_dir}的题单",
                        "category": layer1_dir
                    }
            except:
                meta_info = {
                    "id": f"{layer1_dir}-101",
                    "title": layer1_dir,
                    "description": f"这是一个关于{layer1_dir}的题单",
                    "category": layer1_dir
                }
            
            # 构建sections
            sections = []
            for layer2_list in layer2_lists:
                section = {
                    "title": layer2_list.get('title', ''),
                    "text": layer2_list.get('text', ''),
                    "content": layer2_list.get('content', [])
                }
                sections.append(section)
            
            # 构建layer1题单
            layer1_list = {
                "id": meta_info.get('id', f"{layer1_dir}-101"),
                "title": meta_info.get('title', layer1_dir),
                "description": meta_info.get('description', ''),
                "category": meta_info.get('category', layer1_dir),
                "sections": sections
            }
            
            # 保存文件
            output_path = os.path.join(layer1_path, f"{layer1_dir}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(layer1_list, f, ensure_ascii=False, indent=2)
            
            print(f"已生成 {output_path}")
        
        print("layer1题单生成完成！")
    
    def copy_to_problem_lists(self):
        """复制最终的题单到Problem_Lists文件夹"""
        print("步骤7: 复制题单到Problem_Lists文件夹...")
        
        # 确保目标目录存在
        os.makedirs(PROBLEM_LISTS_DIR, exist_ok=True)
        
        for layer1_dir in os.listdir(SET_FOR_LIST_DIR):
            layer1_path = os.path.join(SET_FOR_LIST_DIR, layer1_dir)
            if not os.path.isdir(layer1_path):
                continue
            
            layer1_list_file = os.path.join(layer1_path, f"{layer1_dir}.json")
            if not os.path.exists(layer1_list_file):
                continue
            
            # 复制到Problem_Lists目录
            dest_file = os.path.join(PROBLEM_LISTS_DIR, f"{layer1_dir}.json")
            shutil.copy2(layer1_list_file, dest_file)
            print(f"已复制 {dest_file}")
        
        print("题单复制完成！")
    
    async def run_reformer(self):
        """运行reformer部分"""
        print("=" * 50)
        print("开始执行Reformer部分")
        print("=" * 50)
        
        self.copy_file_structure()
        await self.generate_solve_and_idea()
        await self.rewrite_problem_jsons()
        
        print("=" * 50)
        print("Reformer部分完成！")
        print("=" * 50)
    
    async def run_combiner(self):
        """运行combiner部分"""
        print("=" * 50)
        print("开始执行Combiner部分")
        print("=" * 50)
        
        await self.combine_layer3_lists()
        await self.combine_layer2_lists()
        await self.combine_layer1_lists()
        self.copy_to_problem_lists()
        
        print("=" * 50)
        print("Combiner部分完成！")
        print("=" * 50)
    
    async def run_all(self):
        """运行完整流程"""
        await self.run_reformer()
        await self.run_combiner()


async def main():
    async with ReformerCombiner() as reformer_combiner:
        await reformer_combiner.run_all()


if __name__ == "__main__":
    asyncio.run(main())