#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
split.py - 切分problem_set中的tutorial和codes字段

对于tutorial：根据题目编号进行切分，只保留与当前题目相关的内容
对于codes：根据题目后缀（A=0, B=1, C=2, ...）选择对应的code
"""

import json
import os
import re
from pathlib import Path


def get_problem_index_number(index: str) -> int:
    """
    将题目后缀转换为数字索引
    A -> 0, B -> 1, C -> 2, ...
    对于复合后缀如 A1, A2, D1, D2 等，需要特殊处理
    """
    # 提取字母部分
    match = re.match(r'([A-Z]+)(\d*)', index)
    if not match:
        return 0
    
    letter = match.group(1)
    number_suffix = match.group(2)
    
    # 将字母转换为数字 (A=0, B=1, ...)
    letter_value = 0
    for char in letter:
        letter_value = letter_value * 26 + (ord(char) - ord('A'))
    
    # 如果有数字后缀（如A1, A2），需要调整
    # A1, A2 等应该映射到 A 的位置附近
    # 这里的处理方式：A1 -> 0, A2 -> 0, B1 -> 1, B2 -> 1
    # 因为 codes 数组是按 A, B, C... 顺序排列的
    
    return letter_value


def split_tutorial(tutorial: str, problem_id: str) -> str:
    """
    从tutorial字符串中提取与当前题目相关的内容
    
    tutorial格式示例：
    "1003A - Polycarp's Pockets\nTutorial\nTutorial is loading...\nSolution (Vovuh)\n1003B - ..."
    
    需要找到以 problem_id 开头的部分，直到下一个题目编号或结尾
    """
    if not tutorial or not tutorial.strip():
        return ""
    
    # 构建匹配模式：题目编号 - 题目名称
    # 例如匹配 "1003A - " 开头的部分
    pattern = r'(\d+[A-Z]\d*(?:\s*-\s*[^\n]+)?)'
    
    # 找到所有题目分隔点
    matches = list(re.finditer(pattern, tutorial))
    
    if not matches:
        # 没有找到分隔模式，返回原内容
        return tutorial
    
    # 找到当前题目的位置
    current_match = None
    current_idx = -1
    for idx, match in enumerate(matches):
        if match.group(1).startswith(problem_id):
            current_match = match
            current_idx = idx
            break
    
    if current_match is None:
        # 没有找到当前题目，可能是因为tutorial格式不同
        # 尝试其他匹配方式
        # 查找 "Problem A.", "Problem B." 等格式
        alt_pattern = r'Problem\s+([A-Z])\.'
        alt_matches = list(re.finditer(alt_pattern, tutorial))
        
        if alt_matches:
            # 提取题目的字母
            letter = problem_id[-1] if problem_id else 'A'
            if not letter.isalpha():
                letter = 'A'
            
            for idx, match in enumerate(alt_matches):
                if match.group(1) == letter:
                    start = match.start()
                    end = alt_matches[idx + 1].start() if idx + 1 < len(alt_matches) else len(tutorial)
                    return tutorial[start:end].strip()
        
        # 尝试匹配 "D2A", "D1A" 等格式
        div_pattern = r'D[12]([A-Z])'
        div_matches = list(re.finditer(div_pattern, tutorial))
        
        if div_matches:
            letter = problem_id[-1] if problem_id else 'A'
            if not letter.isalpha():
                letter = 'A'
            
            for idx, match in enumerate(div_matches):
                if match.group(1) == letter:
                    start = match.start()
                    end = div_matches[idx + 1].start() if idx + 1 < len(div_matches) else len(tutorial)
                    return tutorial[start:end].strip()
        
        return tutorial
    
    # 提取当前题目的内容
    start = current_match.start()
    end = matches[current_idx + 1].start() if current_idx + 1 < len(matches) else len(tutorial)
    
    return tutorial[start:end].strip()


def get_corresponding_code(codes: list, index: str) -> list:
    """
    根据题目后缀获取对应的code
    A -> 第1个code, B -> 第2个code, ...
    """
    if not codes:
        return []
    
    code_index = get_problem_index_number(index)
    
    # 检查索引是否在范围内
    if code_index < 0 or code_index >= len(codes):
        # 如果索引超出范围，返回空列表
        return []
    
    return [codes[code_index]]


def process_problem_file(file_path: Path) -> bool:
    """
    处理单个题目JSON文件
    返回是否进行了修改
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    modified = False
    
    # 处理tutorial
    original_tutorial = data.get('tutorial', '')
    problem_id = data.get('id', '')
    
    if original_tutorial:
        new_tutorial = split_tutorial(original_tutorial, problem_id)
        if new_tutorial != original_tutorial:
            data['tutorial'] = new_tutorial
            modified = True
    
    # 处理codes
    original_codes = data.get('codes', [])
    index = data.get('index', '')
    
    if original_codes and len(original_codes) > 1:
        new_codes = get_corresponding_code(original_codes, index)
        if new_codes != original_codes:
            data['codes'] = new_codes
            modified = True
    
    # 如果进行了修改，保存文件
    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False


def main():
    """
    主函数：遍历problem_set目录，处理所有JSON文件
    """
    problem_set_dir = Path('problem_set')
    
    if not problem_set_dir.exists():
        print(f"Directory {problem_set_dir} does not exist")
        return
    
    total_files = 0
    modified_files = 0
    
    for file_path in problem_set_dir.glob('*.json'):
        total_files += 1
        if process_problem_file(file_path):
            modified_files += 1
            print(f"Modified: {file_path.name}")
    
    print(f"\nTotal files: {total_files}")
    print(f"Modified files: {modified_files}")
    print(f"Unchanged files: {total_files - modified_files}")


if __name__ == '__main__':
    main()