"""
题目进一步分类打标签程序
使用LLM对已分类的题目进行更细粒度的划分
支持断点续传和并发处理
"""

import os
import json
import random
import math
import time
from pathlib import Path
import openai
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-281e934bcc544d2d88b7ba87037d2e00"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 配置OpenAI客户端
client = openai.OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 基础路径（注意：实际题目在嵌套的tidy_problem_set目录下）
BASE_PATH = Path("D:/CODE/CFLister/tidy_problem_set/tidy_problem_set")

# 并发数
MAX_CONCURRENT = 100

# 断点续传文件
PROGRESS_FILE = BASE_PATH / "classification_progress.json"

# 线程锁，用于文件操作
file_lock = Lock()
progress_lock = Lock()


def load_progress() -> Dict[str, Set[str]]:
    """
    加载进度文件
    
    Returns:
        已处理的文件夹和题目集合
    """
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            # 将列表转换为集合
            return {
                folder: set(problems) if isinstance(problems, list) else problems
                for folder, problems in progress.items()
            }
    return {}


def save_progress(progress: Dict[str, Set[str]]) -> None:
    """
    保存进度文件
    
    Args:
        progress: 进度字典
    """
    # 将集合转换为列表以便序列化
    serializable_progress = {
        folder: list(problems) if isinstance(problems, set) else problems
        for folder, problems in progress.items()
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_progress, f, ensure_ascii=False, indent=2)


def update_progress(folder_key: str, problem_id: str) -> None:
    """
    更新进度
    
    Args:
        folder_key: 文件夹标识符
        problem_id: 题目ID
    """
    with progress_lock:
        progress = load_progress()
        if folder_key not in progress:
            progress[folder_key] = set()
        progress[folder_key].add(problem_id)
        save_progress(progress)


def is_folder_processed(folder_path: Path) -> bool:
    """
    检查文件夹是否已处理完毕
    
    Args:
        folder_path: 文件夹路径
    
    Returns:
        是否已处理
    """
    progress = load_progress()
    folder_key = str(folder_path)
    
    if folder_key not in progress:
        return False
    
    # 获取当前文件夹的所有JSON文件
    json_files = list(folder_path.glob("*.json"))
    processed_ids = progress[folder_key]
    
    # 如果所有题目都已处理，返回True
    current_ids = {f.stem for f in json_files}
    return current_ids.issubset(processed_ids)


def call_deepseek_api(prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
    """
    调用DeepSeek API
    
    Args:
        prompt: 输入的prompt
        max_tokens: 最大返回token数
        temperature: 温度参数
    
    Returns:
        API返回的结果
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的算法竞赛题目分类助手，需要根据题目内容进行精准分类。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        raise


def get_problem_summary(problem: Dict) -> str:
    """
    获取题目摘要信息（节省token）
    
    Args:
        problem: 题目JSON数据
    
    Returns:
        题目摘要字符串
    """
    summary = f"题目ID: {problem['id']}, 名称: {problem['name']}, 难度: {problem['difficulty']}\n"
    
    # 标签
    if problem.get('tags'):
        summary += f"标签: {', '.join(problem['tags'])}\n"
    
    # 题目描述（截取前200字符）
    if problem.get('description'):
        desc = problem['description'][:200]
        summary += f"描述: {desc}...\n"
    
    # 教程（截取前150字符）
    if problem.get('tutorial') and len(problem['tutorial']) > 10:
        tutorial = problem['tutorial'][:150]
        summary += f"教程: {tutorial}...\n"
    
    # 代码（取第一个代码的前100字符）
    if problem.get('codes') and len(problem['codes']) > 0:
        code = str(problem['codes'][0])[:100]
        summary += f"代码示例: {code}...\n"
    
    return summary


def check_need_further_division(folder_path: Path, current_tag: str, num_problems: int, current_layer: int) -> bool:
    """
    判断是否需要进一步划分
    
    Args:
        folder_path: 当前文件夹路径
        current_tag: 当前层级的tag
        num_problems: 当前题目数量
        current_layer: 当前层级
    
    Returns:
        是否需要进一步划分
    """
    # 随机抽取45个题目（或全部如果不足45个）
    json_files = list(folder_path.glob("*.json"))
    sample_size = min(45, len(json_files))
    sampled_files = random.sample(json_files, sample_size)
    
    # 构建prompt，增加题目数量和层数的考虑
    prompt = f"""请判断以下{current_tag}类别的题目是否需要进一步细分。

当前类别: {current_tag}
当前层级: layer{current_layer}
该类别总题目数: {num_problems}
抽样题目数: {sample_size}

抽样题目信息:
"""
    
    for i, json_file in enumerate(sampled_files[:10]):  # 只展示前10个以节省token
        with open(json_file, 'r', encoding='utf-8') as f:
            problem = json.load(f)
        prompt += f"\n--- 题目{i+1} ---\n{get_problem_summary(problem)}"
    
    if len(sampled_files) > 10:
        prompt += f"\n... 还有{len(sampled_files)-10}道题目\n"
    
    prompt += f"""
请综合考虑以下因素判断这个类别是否需要进一步细分：
1. 题目的数量（当前{num_problems}道）
2. 当前的分类层级（当前为layer{current_layer}层）
3. 题目的具体特点、解题思路、算法知识点等
4. 题目是否涵盖多种不同的子算法、技巧或知识点

判断标准：
- 如果题目数量较少（少于30道），通常无需细分，返回"无需划分"
- 如果题目数量适中但都属于同一个具体的技术点，返回"无需划分"
- 如果当前层级已经很深（达到5层或6层），通常无需继续细分，返回"无需划分"
- 如果题目涵盖多种不同的子算法、技巧或知识点，需要进一步细分，返回"需要划分"

只返回"需要划分"或"无需划分"，不要其他内容。"""
    
    logger.info(f"检查文件夹 {folder_path.name} 是否需要进一步划分（题目数: {num_problems}，层级: {current_layer}）...")
    response = call_deepseek_api(prompt, max_tokens=50, temperature=0.2)
    
    need_division = "需要划分" in response
    logger.info(f"文件夹 {folder_path.name} {'需要' if need_division else '无需'}进一步划分")
    
    return need_division


def get_sub_tags_suggestions(folder_path: Path, current_tag: str) -> Set[str]:
    """
    获取子类tag建议（单次调用）
    
    Args:
        folder_path: 当前文件夹路径
        current_tag: 当前层级的tag
    
    Returns:
        子类tag集合
    """
    # 随机抽取45个题目
    json_files = list(folder_path.glob("*.json"))
    sample_size = min(45, len(json_files))
    sampled_files = random.sample(json_files, sample_size)
    
    # 构建prompt，使用所有抽取题目的完整信息
    prompt = f"""请为以下{current_tag}类别的题目建议合适的细分分类。

当前类别: {current_tag}
抽样题目数: {sample_size}

抽样题目信息:
"""
    
    # 展示所有抽取的题目（完整信息）
    for i, json_file in enumerate(sampled_files):
        with open(json_file, 'r', encoding='utf-8') as f:
            problem = json.load(f)
        prompt += f"\n--- 题目{i+1} ---\n{get_problem_summary(problem)}"
    
    prompt += f"""
根据这些题目的具体特点、解题思路、算法知识点等，建议将{current_tag}进一步细分为哪几个子类别？
要求：
1. 子类别应该是{current_tag}下的具体技术点、算法变种或应用场景
2. 每个子类别名称应该简洁明确（例如：如果当前是DP，子类别可以是"背包"、"状态压缩DP"、"树状DP"等）
3. 子类别之间应该互斥且有区分度
4. 列出3-6个子类别

请按以下格式返回（每行一个子类别）：
子类别1
子类别2
子类别3
...
"""
    
    logger.info(f"获取文件夹 {folder_path.name} 的子类tag建议（抽样{sample_size}道题）...")
    response = call_deepseek_api(prompt, max_tokens=500, temperature=0.5)
    
    # 解析返回的子类别
    sub_tags = set()
    for line in response.split('\n'):
        line = line.strip()
        if line and not line.startswith('子类别'):
            sub_tags.add(line)
    
    logger.info(f"获得 {len(sub_tags)} 个子类tag建议: {sub_tags}")
    
    return sub_tags


def merge_similar_tags(tag_sets: List[Set[str]]) -> Set[str]:
    """
    合并相似的tag
    
    Args:
        tag_sets: 多次调用获得的tag集合列表
    
    Returns:
        合并后的tag集合
    """
    # 取并集
    all_tags = set()
    for tag_set in tag_sets:
        all_tags.update(tag_set)
    
    if not all_tags:
        return all_tags
    
    # 构建prompt合并相似tag
    prompt = f"""以下是通过多次抽样获得的所有细分分类标签建议：

{chr(10).join(sorted(all_tags))}

其中一些标签可能表达相同或相似的含义。请合并这些标签，保留最合适的表述。
要求：
1. 识别并合并含义相同或非常相似的标签（例如"01背包"和"0/1背包"应该合并）
2. 每个合并后的标签名称应该简洁明确
3. 最终保留3-8个最有代表性的标签

请按以下格式返回（每行一个最终标签）：
最终标签1
最终标签2
最终标签3
...
"""
    
    logger.info("合并相似的tag...")
    response = call_deepseek_api(prompt, max_tokens=300, temperature=0.3)
    
    # 解析合并后的标签
    merged_tags = set()
    for line in response.split('\n'):
        line = line.strip()
        if line and not line.startswith('最终标签'):
            merged_tags.add(line)
    
    logger.info(f"合并后得到 {len(merged_tags)} 个子类tag: {merged_tags}")
    
    return merged_tags


def classify_problem(problem: Dict, sub_tags: Set[str], current_tag: str) -> str:
    """
    将题目分类到具体的子类tag
    
    Args:
        problem: 题目JSON数据
        sub_tags: 子类tag集合
        current_tag: 当前层级的tag
    
    Returns:
        最合适的子类tag
    """
    # 构建prompt
    available_tags = sorted(sub_tags)
    prompt = f"""请将以下题目分类到最合适的子类别。

当前类别: {current_tag}
可用的子类别:
{chr(10).join([f"{i+1}. {tag}" for i, tag in enumerate(available_tags)])}

题目信息:
{get_problem_summary(problem)}

请根据题目的具体特点、解题思路、算法知识点等，选择最合适的子类别。
只返回子类别的名称，不要其他内容。"""
    
    response = call_deepseek_api(prompt, max_tokens=50, temperature=0.2)
    
    # 确保返回的tag在可用列表中
    response = response.strip()
    if response in sub_tags:
        return response
    
    # 如果不在列表中，尝试模糊匹配
    for tag in sub_tags:
        if tag in response or response in tag:
            return tag
    
    # 如果无法匹配，随机选择一个（或者选择第一个）
    logger.warning(f"无法将题目 {problem['id']} 分类到返回的结果 '{response}'，选择第一个子类别")
    return available_tags[0]


def sanitize_folder_name(name: str) -> str:
    """
    清理文件夹名称，移除Windows不允许的字符
    
    Args:
        name: 原始名称
    
    Returns:
        清理后的名称
    """
    # Windows不允许的字符: < > : " / \ | ? *
    # 以及保留的设备名称: CON, PRN, AUX, NUL, COM1-9, LPT1-9
    
    # 替换不允许的字符
    for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        name = name.replace(char, '-')
    
    # 移除前后空格
    name = name.strip()
    
    # 确保不为空
    if not name:
        name = "unnamed"
    
    return name


def classify_single_problem(args: Tuple[Path, Dict, Set[str], str, int, Dict[str, str], str]) -> Tuple[str, str, Optional[Exception]]:
    """
    分类单个题目（用于并发处理）
    
    Args:
        args: (json_file, problem, final_sub_tags, current_tag, layer_key, tag_name_mapping, folder_key)
    
    Returns:
        (problem_id, classified_tag, error)
    """
    json_file, problem, final_sub_tags, current_tag, layer_key, tag_name_mapping, folder_key = args
    
    try:
        problem_id = problem['id']
        
        # 获取分类结果
        classified_tag = classify_problem(problem, final_sub_tags, current_tag)
        
        # 更新JSON文件（使用原始标签）
        problem[layer_key] = classified_tag
        
        # 写入原文件（使用锁保证线程安全）
        with file_lock:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(problem, f, ensure_ascii=False, indent=2)
            
            # 移动到对应的子文件夹（使用清理后的名称）
            cleaned_tag = tag_name_mapping[classified_tag]
            sub_folder = json_file.parent / cleaned_tag
            new_path = sub_folder / json_file.name
            
            # 移动文件
            json_file.rename(new_path)
        
        # 更新进度
        update_progress(folder_key, problem_id)
        
        logger.info(f"题目 {problem_id} 分类为 {classified_tag}，移动到 {new_path}")
        return (problem_id, classified_tag, None)
        
    except Exception as e:
        logger.error(f"分类题目 {problem.get('id', 'unknown')} 失败: {e}")
        return (problem.get('id', 'unknown'), '', e)


def process_folder(folder_path: Path, current_layer: int) -> None:
    """
    处理文件夹，进行进一步分类
    
    Args:
        folder_path: 文件夹路径
        current_layer: 当前层级
    """
    folder_key = str(folder_path)
    
    # 检查是否已处理
    if is_folder_processed(folder_path):
        logger.info(f"文件夹 {folder_path} 已处理，跳过")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"开始处理文件夹: {folder_path} (层级: {current_layer})")
    logger.info(f"{'='*60}")
    
    # 获取所有JSON文件
    json_files = list(folder_path.glob("*.json"))
    num_problems = len(json_files)
    
    if num_problems == 0:
        logger.info(f"文件夹 {folder_path} 没有题目文件，跳过")
        return
    
    logger.info(f"文件夹 {folder_path} 包含 {num_problems} 道题目")
    
    # 获取当前层级的tag名称
    current_tag = folder_path.name
    
    # 读取第一个文件获取当前最高layer
    with open(json_files[0], 'r', encoding='utf-8') as f:
        sample_problem = json.load(f)
    
    max_layer = 0
    for key in sample_problem.keys():
        if key.startswith('layer') and key.endswith('_tag'):
            layer_num = int(key.replace('layer', '').replace('_tag', ''))
            max_layer = max(max_layer, layer_num)
    
    logger.info(f"当前最高层级: layer{max_layer}")
    
    # 步骤2: 判断是否需要进一步划分（传入当前层级）
    need_division = check_need_further_division(folder_path, current_tag, num_problems, current_layer)
    
    if not need_division:
        logger.info(f"文件夹 {folder_path} 无需进一步划分，结束")
        # 标记为已处理
        with progress_lock:
            progress = load_progress()
            progress[folder_key] = {f.stem for f in json_files}
            save_progress(progress)
        return
    
    # 步骤3: 获取子类tag建议，进行 log2N 次（并发处理）
    num_iterations = max(1, int(math.log2(num_problems)))
    tag_sets = []
    
    logger.info(f"将并发进行 {num_iterations} 次子类tag获取")
    
    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(get_sub_tags_suggestions, folder_path, current_tag): i
            for i in range(num_iterations)
        }
        
        # 等待任务完成并收集结果
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                sub_tags = future.result()
                tag_sets.append(sub_tags)
                logger.info(f"第 {index+1}/{num_iterations} 次获取子类tag完成")
            except Exception as e:
                logger.error(f"第 {index+1}/{num_iterations} 次获取子类tag失败: {e}")
    
    logger.info(f"所有 {len(tag_sets)} 次子类tag获取完成")
    
    # 步骤4: 合并相似的tag
    final_sub_tags = merge_similar_tags(tag_sets)
    
    if not final_sub_tags:
        logger.warning(f"文件夹 {folder_path} 没有获得有效的子类tag，停止划分")
        return
    
    # 步骤5: 创建子类文件夹（清理标签名称）
    tag_name_mapping = {}  # 原始标签 -> 清理后的文件夹名称
    for sub_tag in final_sub_tags:
        cleaned_name = sanitize_folder_name(sub_tag)
        tag_name_mapping[sub_tag] = cleaned_name
        # 使用Path对象来处理路径，避免斜杠被解释为路径分隔符
        sub_folder = folder_path / Path(cleaned_name)
        sub_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建子文件夹: {sub_folder} (原标签: {sub_tag})")
    
    # 步骤6: 并发处理每个题目
    next_layer = max_layer + 1
    layer_key = f"layer{next_layer}_tag"
    
    logger.info(f"开始并发分类 {num_problems} 道题目（并发数: {MAX_CONCURRENT}）...")
    
    # 准备并发任务参数
    tasks = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            problem = json.load(f)
        tasks.append((json_file, problem, final_sub_tags, current_tag, layer_key, tag_name_mapping, folder_key))
    
    # 使用线程池并发处理
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(classify_single_problem, task): task[1]['id']
            for task in tasks
        }
        
        # 等待任务完成
        for future in as_completed(future_to_task):
            problem_id = future_to_task[future]
            try:
                result = future.result()
                if result[2] is None:  # 没有错误
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"处理题目 {problem_id} 时发生异常: {e}")
                fail_count += 1
    
    logger.info(f"文件夹 {folder_path} 的所有题目分类完成: 成功 {success_count}, 失败 {fail_count}, 共分类到 {len(final_sub_tags)} 个子类别")
    
    # 步骤7: 递归处理子文件夹（使用清理后的名称）
    for sub_tag in final_sub_tags:
        cleaned_tag = tag_name_mapping[sub_tag]
        sub_folder = folder_path / cleaned_tag
        process_folder(sub_folder, next_layer)


def generate_hierarchy_tree(base_path: Path, output_file: str = "hierarchy_tree.txt") -> None:
    """
    生成层级结构图
    
    Args:
        base_path: 基础路径
        output_file: 输出文件名
    """
    logger.info(f"\n生成层级结构图...")
    
    output_path = base_path / output_file
    
    def build_tree(path: Path, prefix: str = "", is_last: bool = True) -> str:
        """
        递归构建树形结构字符串
        """
        if not path.exists():
            return ""
        
        # 获取所有JSON文件和子文件夹
        items = sorted(list(path.glob("*")))
        json_files = [f for f in items if f.is_file() and f.suffix == '.json']
        folders = [f for f in items if f.is_dir()]
        
        result = f"{prefix}{'└── ' if is_last else '├── '}{path.name}/ ({len(json_files)} 道题)\n"
        
        # 处理子文件夹
        if folders:
            # 按layer层级排序（通过读取文件夹内文件的最大layer值）
            def get_folder_depth(folder: Path) -> int:
                json_files = list(folder.glob("*.json"))
                if not json_files:
                    return 0
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    problem = json.load(f)
                max_layer = 0
                for key in problem.keys():
                    if key.startswith('layer') and key.endswith('_tag'):
                        layer_num = int(key.replace('layer', '').replace('_tag', ''))
                        max_layer = max(max_layer, layer_num)
                return max_layer
            
            folders.sort(key=get_folder_depth)
            
            for i, folder in enumerate(folders):
                is_last_folder = (i == len(folders) - 1)
                new_prefix = prefix + ("    " if is_last else "│   ")
                result += build_tree(folder, new_prefix, is_last_folder)
        
        return result
    
    tree_str = "题目分类层级结构图\n"
    tree_str += "=" * 80 + "\n\n"
    
    # 获取所有顶级文件夹
    top_folders = sorted([f for f in base_path.glob("*") if f.is_dir()])
    
    for i, folder in enumerate(top_folders):
        is_last = (i == len(top_folders) - 1)
        tree_str += build_tree(folder, "", is_last)
        tree_str += "\n"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(tree_str)
    
    logger.info(f"层级结构图已生成: {output_path}")


def main():
    """
    主函数
    """
    logger.info("="*80)
    logger.info("开始题目进一步分类程序")
    logger.info(f"并发数: {MAX_CONCURRENT}")
    logger.info(f"断点续传文件: {PROGRESS_FILE}")
    logger.info("="*80)
    
    # 检查是否有之前的进度
    progress = load_progress()
    if progress:
        logger.info(f"发现之前的进度，已处理 {len(progress)} 个文件夹")
        logger.info("程序将跳过已处理的文件夹，实现断点续传")
    
    # 遍历tidy_problem_set下的所有一级文件夹
    top_folders = [f for f in BASE_PATH.glob("*") if f.is_dir()]
    
    logger.info(f"发现 {len(top_folders)} 个顶级文件夹")
    
    start_time = time.time()
    
    for folder in top_folders:
        process_folder(folder, 1)
    
    # 生成层级结构图
    generate_hierarchy_tree(BASE_PATH)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logger.info("="*80)
    logger.info(f"题目分类程序完成！")
    logger.info(f"总耗时: {elapsed_time:.2f} 秒")
    logger.info("="*80)


if __name__ == "__main__":
    main()