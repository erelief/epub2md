# EPUB转换器测试套件

## 📋 测试文件说明

### 测试文件
- `test_integration.py` - 集成测试，测试完整的转换流程
- `test_edge_cases.py` - 边缘情况测试，测试异常情况和错误处理
- `run_all_tests.py` - 测试运行器，执行所有测试并生成报告
- `TEST_DOCUMENTATION.md` - 详细的测试文档和说明

## 🚀 运行测试

### 运行所有测试（推荐）
```bash
# 在项目根目录运行
python tests/run_all_tests.py
```

### 运行单个测试文件
```bash
# 运行集成测试
python -m unittest tests.test_integration

# 运行边缘情况测试
python -m unittest tests.test_edge_cases
```

### 运行特定测试方法
```bash
# 运行特定的测试方法
python -m unittest tests.test_integration.TestEPUBIntegration.test_basic_conversion
```

## 📊 测试覆盖范围

### 集成测试 (test_integration.py)
- ✅ 基本EPUB转换功能
- ✅ 中文内容处理
- ✅ 图片提取和链接
- ✅ 封面处理
- ✅ 多章节书籍
- ✅ 输出目录结构
- ✅ 文件命名规则

### 边缘情况测试 (test_edge_cases.py)
- ✅ 损坏的EPUB文件
- ✅ 空内容处理
- ✅ 特殊字符文件名
- ✅ 大文件处理
- ✅ 权限问题
- ✅ 网络链接处理
- ✅ 编码问题

## 🔧 测试环境要求

### 系统要求
- Python 3.7+
- html2text >= 2020.1.16
- 足够的临时目录空间（约100MB）

### 运行前准备
```bash
# 确保依赖已安装
pip install -r requirements.txt

# 确保在项目根目录
cd /path/to/epub-converter
```

## 📝 测试结果说明

### 成功输出示例
```
EPUB到Markdown转换器 - 完整测试套件
======================================================================

运行 集成测试 / Integration Tests 测试套件...
--------------------------------------------------
集成测试 / Integration Tests 结果:
  通过: 8/8
  失败: 0
  错误: 0

运行 边缘情况测试 / Edge Case Tests 测试套件...
--------------------------------------------------
边缘情况测试 / Edge Case Tests 结果:
  通过: 6/6
  失败: 0
  错误: 0

======================================================================
测试结果摘要 / Test Results Summary
======================================================================
总测试数 / Total Tests: 14
通过 / Passed: 14
失败 / Failed: 0
错误 / Errors: 0
跳过 / Skipped: 0
测试时间 / Duration: 12.34 秒
成功率 / Success Rate: 100.0%
======================================================================

✅ 所有测试通过
```

### 失败输出示例
```
======================================================================
测试结果摘要 / Test Results Summary
======================================================================
总测试数 / Total Tests: 14
通过 / Passed: 12
失败 / Failed: 2
错误 / Errors: 0
跳过 / Skipped: 0
测试时间 / Duration: 15.67 秒
成功率 / Success Rate: 85.7%

失败的测试 / Failed Tests:
  - test_basic_conversion: FAIL
    AssertionError: Expected 3 files, got 2
  - test_image_extraction: FAIL
    FileNotFoundError: Image file not found
======================================================================

❌ 部分测试失败
```

## 🐛 故障排除

### 常见问题

**问题1：导入模块失败**
```
ModuleNotFoundError: No module named 'epub_converter'
```
**解决方案**：确保在项目根目录运行测试

**问题2：临时目录权限问题**
```
PermissionError: [Errno 13] Permission denied
```
**解决方案**：检查临时目录权限或以管理员身份运行

**问题3：依赖包缺失**
```
ModuleNotFoundError: No module named 'html2text'
```
**解决方案**：安装依赖包 `pip install html2text`

### 调试技巧

1. **增加详细输出**
   ```bash
   python tests/run_all_tests.py -v
   ```

2. **运行单个测试进行调试**
   ```bash
   python -m unittest tests.test_integration.TestEPUBIntegration.test_basic_conversion -v
   ```

3. **检查测试生成的临时文件**
   - 测试失败时，临时文件可能保留在系统临时目录
   - 可以手动检查这些文件来诊断问题

## 📈 添加新测试

### 添加集成测试
在 `test_integration.py` 中添加新的测试方法：
```python
def test_new_feature(self):
    """测试新功能"""
    # 测试代码
    pass
```

### 添加边缘情况测试
在 `test_edge_cases.py` 中添加新的测试方法：
```python
def test_edge_case(self):
    """测试边缘情况"""
    # 测试代码
    pass
```

### 测试命名规范
- 测试方法必须以 `test_` 开头
- 使用描述性的方法名
- 添加文档字符串说明测试目的

---

更多详细信息请参考 `TEST_DOCUMENTATION.md`