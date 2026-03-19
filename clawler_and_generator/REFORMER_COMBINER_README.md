# Reformer & Combiner - 题目题单整合程序

## 功能说明

本程序用于将零散的JSON题目文件整合成为几个大的题单JSON，分为两个主要部分：

### Reformer 部分
1. **文件结构重组**：将 `tidy_problem_set` 下的所有文件复制到 `set_for_list` 目录，保留3级文件夹结构，将深层文件夹的题目合并到对应的layer3_tag层级
2. **生成solve_and_idea.json**：为每个layer3_tag目录生成解题思路和代码模板
3. **改写题目JSON**：调用API改写每个题目JSON，添加解题分析note字段

### Combiner 部分
1. **生成layer3题单**：将每个layer3_tag目录的题目和solve_and_idea.json合并为题单
2. **生成layer2题单**：将layer3题单合并到layer2层级，生成章节概要
3. **生成layer1题单**：将layer2题单合并到layer1层级，生成题单描述
4. **复制到problem_lists**：将最终题单复制到problem_lists文件夹

## 使用方法

### 环境要求
- Python 3.7+
- conda环境（推荐使用CFL环境）
- 依赖包：aiohttp

### 安装依赖
```bash
conda activate CFL
pip install aiohttp
```

### 运行程序
```bash
conda activate CFL
python reformer_combiner.py
```

## 配置说明

程序开头的配置项：

```python
# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-281e934bcc544d2d88b7ba87037d2e00"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 目录配置
TIDY_PROBLEM_SET_DIR = "tidy_problem_set"  # 源目录
SET_FOR_LIST_DIR = "set_for_list"          # 中间目录
PROBLEM_LISTS_DIR = "problem_lists"        # 最终输出目录

# 并发配置
MAX_CONCURRENT_REQUESTS = 200  # 最大并发API请求数
```

## 输出结构

### 最终题单JSON格式（layer1）

```json
{
  "id": "greedy-101",
  "title": "贪心算法题单",
  "description": "为方便大家练习，我把比较套路的贪心题目放在前面……",
  "category": "贪心算法",
  "sections": [
    {
      "title": "排序与选择",
      "text": "在贪心的排序与选择做法中，又可以分为几类....",
      "content": [
        {
          "title": "§中位数与第K大元素",
          "code_template": "/* 板子代码示例 */\nint main() { return 0; }",
          "idea": "优先考虑最小/最大的数，从小到大/从大到小贪心。",
          "problems": [
            {
              "id": "3074a",
              "name": "重新分装苹果",
              "difficulty": 1198,
              "tags": ["greedy", "sorting"],
              "url": "https://codeforces.com/contest/3074/problem/A",
              "note": "从最小箱子开始贪心"
            }
          ]
        }
      ]
    }
  ]
}
```

## 注意事项

1. **API调用次数**：程序会调用大量API请求（可能数千次），请确保API配额充足
2. **运行时间**：完整运行可能需要数小时，建议在后台运行
3. **错误处理**：程序对API调用失败有容错机制，会使用默认模板继续执行
4. **并发限制**：默认最大并发数为200，可根据网络状况调整
5. **中间结果**：程序会在 `set_for_list` 目录保存中间结果，可以手动检查
6. **断点续传**：程序支持断点续传，已生成的文件会被自动跳过，节省API调用
7. **难度为空的题目**：difficulty为NULL的题目也会被加入题单，放在最末尾

## 输出目录说明

- `tidy_problem_set/` - 源题目目录
- `set_for_list/` - 中间处理目录（包含所有中间文件）
  - layer1_tag/layer2_tag/layer3_tag/ - 题目文件
  - layer1_tag/layer2_tag/layer3_tag/solve_and_idea.json - 解题思路
  - layer1_tag/layer2_tag/layer3_tag/layer3_tag.json - layer3题单
  - layer1_tag/layer2_tag/layer2_tag.json - layer2题单
  - layer1_tag/layer1_tag.json - layer1题单
- `problem_lists/` - 最终题单目录（只包含layer1题单）

## 故障排查

### API调用失败
如果遇到大量API调用失败，请检查：
1. API Key是否正确
2. 网络连接是否正常
3. API配额是否充足

### 权限错误
如果遇到权限错误，请确保：
1. 没有其他程序正在访问 `set_for_list` 目录
2. 关闭所有打开的文件或编辑器

### 内存不足
如果遇到内存不足，可以：
1. 减少 `MAX_CONCURRENT_REQUESTS` 的值
2. 分批处理题目

## 更新日志

- 初始版本：实现reformer和combiner功能
- 支持DeepSeek API调用
- 支持并发处理（最大200并发）
- 自动错误处理和重试