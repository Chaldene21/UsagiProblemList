"""
测试prompter_tagger.py的基本功能
只处理一个小文件夹来测试程序是否正常工作
"""

import sys
from pathlib import Path
import json

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from prompter_tagger import (
    call_deepseek_api,
    get_problem_summary,
    check_need_further_division,
    get_sub_tags_suggestions,
    merge_similar_tags,
    classify_problem
)

def test_api_call():
    """测试API调用"""
    print("="*60)
    print("测试1: API调用")
    print("="*60)
    
    try:
        response = call_deepseek_api("你好，请回复'测试成功'", max_tokens=10, temperature=0.1)
        print(f"API响应: {response}")
        if "测试" in response or "成功" in response:
            print("[PASS] API调用测试通过")
            return True
        else:
            print("[FAIL] API响应不符合预期")
            return False
    except Exception as e:
        print(f"[FAIL] API调用测试失败: {e}")
        return False


def test_problem_summary():
    """测试题目摘要生成"""
    print("\n" + "="*60)
    print("测试2: 题目摘要生成")
    print("="*60)
    
    # 加载一个测试题目
    test_file = Path("D:/CODE/CFLister/tidy_problem_set/binary-search/16C.json")
    
    if not test_file.exists():
        print(f"[FAIL] 测试文件不存在: {test_file}")
        return False
    
    with open(test_file, 'r', encoding='utf-8') as f:
        problem = json.load(f)
    
    summary = get_problem_summary(problem)
    print(f"生成的摘要:\n{summary}")
    print("[PASS] 题目摘要生成测试通过")
    return True


def test_small_folder():
    """测试处理一个小文件夹"""
    print("\n" + "="*60)
    print("测试3: 处理小文件夹")
    print("="*60)
    
    # 选择一个题目数量较少的文件夹进行测试
    test_folder = Path("D:/CODE/CFLister/tidy_problem_set/constructive")
    
    if not test_folder.exists():
        print(f"[FAIL] 测试文件夹不存在: {test_folder}")
        return False
    
    json_files = list(test_folder.glob("*.json"))
    num_problems = len(json_files)
    
    print(f"测试文件夹: {test_folder}")
    print(f"题目数量: {num_problems}")
    
    if num_problems == 0:
        print("[FAIL] 文件夹中没有题目")
        return False
    
    # 测试判断是否需要进一步划分
    print("\n测试判断是否需要进一步划分...")
    current_tag = test_folder.name
    
    try:
        need_division = check_need_further_division(test_folder, current_tag, num_problems)
        print(f"是否需要进一步划分: {need_division}")
        print("[PASS] 判断是否需要划分测试通过")
        
        # 如果需要划分，测试获取子类tag
        if need_division:
            print("\n测试获取子类tag建议...")
            sub_tags = get_sub_tags_suggestions(test_folder, current_tag)
            print(f"获得的子类tag: {sub_tags}")
            
            # 测试合并相似tag
            print("\n测试合并相似tag...")
            tag_sets = [sub_tags]
            merged_tags = merge_similar_tags(tag_sets)
            print(f"合并后的tag: {merged_tags}")
            
            # 测试分类单个题目
            if merged_tags:
                print("\n测试分类单个题目...")
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    problem = json.load(f)
                classified_tag = classify_problem(problem, merged_tags, current_tag)
                print(f"题目 {problem['id']} 分类为: {classified_tag}")
        
        print("[PASS] 小文件夹处理测试通过")
        return True
        
    except Exception as e:
        print(f"[FAIL] 小文件夹处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("开始测试 prompter_tagger.py")
    print("="*80)
    
    tests = [
        ("API调用", test_api_call),
        ("题目摘要生成", test_problem_summary),
        ("小文件夹处理", test_small_folder)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[FAIL] 测试 '{test_name}' 发生异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！程序可以正常运行。")
    else:
        print(f"\n[WARNING] 有 {total - passed} 个测试失败，请检查程序配置和代码。")


if __name__ == "__main__":
    main()