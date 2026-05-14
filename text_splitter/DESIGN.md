# 文本分割器完整技术方案

## 项目信息

- **项目名称**: text_splitter
- **版本**: v1.0.0
- **创建日期**: 2025-12-31
- **项目定位**: 独立的命令行工具，将长文本文件按章节自动分割成多个规范命名的Markdown文件
- **与epub_converter的关系**:
  - epub_converter: EPUB → 多个MD文件
  - text_splitter: 长文本 → 多个MD文件
  - 两者输出格式完全一致，可配合使用

---

## 1. 项目结构

```
text_splitter/
├── __init__.py                  # 包初始化
├── __main__.py                  # 模块入口点
├── main.py                      # 主程序和CLI
├── file_reader.py               # 文件读取器
├── chapter_detector.py          # 章节检测器
├── content_splitter.py          # 内容分割器
├── format_converter.py          # 格式转换器
├── file_manager.py              # 文件管理器
├── language_detector.py         # 语言检测器（复用epub_converter）
├── utils.py                     # 工具函数
│
├── text_splitter.bat            # Windows启动脚本
├── setup.py                     # 安装配置
├── requirements.txt             # 依赖清单
└── README.md                    # 使用文档

tests/
├── test_file_reader.py          # 文件读取测试
├── test_chapter_detector.py     # 章节检测测试
├── test_integration.py          # 集成测试
└── sample_files/                # 测试样本文件
    ├── novel.txt
    ├── novel.docx
    └── novel.md
```

---

## 2. 核心模块设计

### 2.1 file_reader.py - 文件读取器

**功能**: 统一读取多种格式的文本文件

**支持的文件格式**:
- `.txt` - 纯文本
- `.md` / `.markdown` - Markdown
- `.docx` - Word 2007+
- `.doc` - 旧版Word

**主要类**:
```python
class FileReader:
    SUPPORTED_FORMATS = {
        '.txt': 'text',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.docx': 'docx',
        '.doc': 'doc'
    }

    def read(file_path: str) -> dict:
        """读取文件，返回统一格式"""
        # 返回: {
        #   'content': str,
        #   'format': str,
        #   'encoding': str,
        #   'metadata': dict,
        #   'has_formatting': bool
        # }
```

**依赖库**:
- `chardet` - 检测文件编码
- `python-docx` - 读取docx文件
- `pywin32` (可选) - 读取旧版doc文件

---

### 2.2 chapter_detector.py - 章节检测器

**功能**: 识别文本中的章节分割点

**内置章节模式** (按优先级):

| 模式名称 | 正则表达式 | 示例 | 说明 |
|---------|-----------|------|------|
| chinese_chapter | `^第[零一二三四五六七八九十百千万0-9]+[章节集卷部回篇]` | 第一章、第一集 | 中文章节/集/卷/部/回/篇 |
| english_chapter | `^Chapter\s+[0-9]+` | Chapter 1, Chapter 01 | 英文章节 |
| episode | `^(?:Episode\|Ep\|EP)\s*[0-9]+` | Episode 1, ep01 | 剧集 |
| part | `^Part\s+[0-9IVXLCDM]+` | Part 1, Part I | 部分 |
| book | `^Book\s+[0-9IVXLCDM]+` | Book 1, Book I | 书籍 |
| numbered | `^[0-9]+\.` | 1. 2. 3. | 数字编号 |

**主要类**:
```python
@dataclass
class ChapterPoint:
    index: int              # 章节序号
    title: str              # 章节标题
    start_position: int     # 在文本中的起始位置
    line_number: int        # 行号
    pattern_type: str       # 匹配的模式类型
    context: str            # 上下文预览

class ChapterDetector:
    def detect_chapters(text: str, min_content_length: int = 100) -> List[ChapterPoint]
    def preview_chapters(chapters: List[ChapterPoint]) -> str
```

**特性**:
- 支持中英文章节格式
- 自动过滤内容过短的章节
- 提供上下文预览
- 可扩展自定义模式

---

### 2.3 content_splitter.py - 内容分割器

**功能**: 根据检测到的章节点分割内容

**主要类**:
```python
@dataclass
class ChapterContent:
    index: int          # 章节序号
    title: str          # 章节标题
    content: str        # 章节内容
    word_count: int     # 字数

class ContentSplitter:
    def split_content(text: str) -> List[ChapterContent]
```

**分割逻辑**:
1. 按章节分割点的start_position切分文本
2. 移除章节标题行（避免重复）
3. 计算每章字数
4. 处理最后一章的特殊情况

---

### 2.4 format_converter.py - 格式转换器

**功能**: 将docx格式转换为Markdown

**格式映射**:

| docx格式 | Markdown格式 |
|---------|-------------|
| Heading 1 | `# 标题` |
| Heading 2 | `## 标题` |
| Heading 3-6 | `###`-`######` |
| 粗体 | `**文本**` |
| 斜体 | `*文本*` |
| 粗体+斜体 | `***文本***` |
| 下划线 | `<u>文本</u>` |
| 删除线 | `~~文本~~` |

**主要类**:
```python
class FormatConverter:
    @staticmethod
    def docx_to_markdown(file_path: str) -> dict:
        """将docx转换为Markdown"""
        # 返回: {
        #   'content': str,      # Markdown内容
        #   'images': list,      # 图片信息
        #   'metadata': dict     # 元数据
        # }

    @staticmethod
    def _apply_run_formatting(paragraph) -> str:
        """应用文本格式标记"""
```

**依赖库**:
- `python-docx` - 读取Word文档

---

### 2.5 file_manager.py - 文件管理器

**功能**: 参考epub_converter的命名规范，输出统一序号的md文件

**文件命名规则**:
- 格式: `序号_章节标题.md`
- 序号: 两位数字，不足补零 (`01_`, `02_`, `03_`)
- 标题: 清理Windows非法字符 (`<>:"/\|?*`)
- 自动移除标题中的重复序号前缀

**主要类**:
```python
class FileManager:
    INVALID_CHARS = r'[<>:"/\\|?*]'

    def sanitize_filename(filename: str) -> str
    def generate_filename(index: int, title: str) -> str
    def save_chapters(chapters: List, output_dir: str = None) -> List[str]
```

**清理规则**:
1. 移除Windows非法字符 → 替换为下划线
2. 移除首尾空格和点
3. 多个空格 → 单个下划线
4. 限制文件名长度 ≤ 200字符
5. 移除标题中的序号前缀（避免重复）
6. 清理后为空 → 使用默认名称 `chapter_序号`

---

### 2.6 main.py - 主程序

**功能**: CLI界面和流程控制

**主要类**:
```python
class TextSplitter:
    def __init__(input_file: str, output_dir: str = None, verbose: bool = False)
    def split() -> dict
```

**处理流程**:
```
1. 读取文件 (FileReader)
   ↓
2. 检测章节 (ChapterDetector)
   ↓
3. 显示预览并确认
   ↓
4. 分割内容 (ContentSplitter)
   ↓
5. 保存文件 (FileManager)
   ↓
6. 显示统计信息
```

**CLI参数**:
```bash
python -m text_splitter [输入文件] [选项]

选项:
  -o, --output    输出目录
  -v, --verbose   显示详细信息
  --version       显示版本号
```

**交互模式**:
- 无参数运行 → 交互式输入文件路径
- 有参数运行 → 直接处理

---

## 3. 命令行接口

### 基本使用

```bash
# 交互式模式
python -m text_splitter

# 直接转换
python -m text_splitter novel.txt

# 指定输出目录
python -m text_splitter -o /output/path novel.docx

# 显示详细信息
python -m text_splitter -v novel.txt
```

### Windows批处理

```batch
# 运行批处理脚本
text_splitter.bat

# 带参数运行
text_splitter.bat novel.txt
```

---

## 4. 用户交互流程

```
1. 用户启动程序
   ↓
2. 选择/输入文件路径
   ↓
3. 程序读取文件并检测章节
   ↓
4. 显示检测到的章节列表（预览）
   ┌─────────────────────────────────┐
   │ 检测到 10 个章节分割点：         │
   │ ========================================
   │ 1. 第一章 (行1, 模式: chinese_chapter)│
   │ 2. 第二章 (行150, 模式: chinese_chapter)│
   │ 3. 第三章 (行300, 模式: chinese_chapter)│
   │ ...                              │
   │ ========================================
   │ 是否继续分割？                   │
   │ [Y] 是，开始分割                  │
   │ [N] 否，取消操作                  │
   └─────────────────────────────────┘
   ↓
5. 执行分割，保存为md文件
   ↓
6. 显示完成信息
   ========================================
   ✓ 分割完成！
   ========================================
   输出目录: /path/to/output/
   分割文件: 10 个
   处理时间: 2.5秒
```

---

## 5. 输出格式

### 目录结构

```
MyNovel/                          # 输出目录（与输入文件同名）
├── 01_第一章.md                  # 章节文件
├── 02_第二章.md
├── 03_第三章.md
├── 04_第四章.md
└── ...
```

### 文件内容示例

**01_第一章.md**:
```markdown
# 第一章 开始

这里是第一章的内容...

正文内容继续...

---

（章节结束）
```

---

## 6. 依赖库

### requirements.txt

```
python-docx>=0.8.11
chardet>=5.0.0
```

### 可选依赖

```
pywin32>=305  # 用于读取旧版.doc文件（仅Windows）
```

---

## 7. 与epub_converter的协调

### 设计原则

1. **独立工具**: 两个独立的Python包
2. **输出一致**: 使用相同的文件命名规则
3. **功能互补**:
   - epub_converter处理EPUB格式
   - text_splitter处理长文本格式

### 配合使用场景

```
场景1: EPUB电子书 → MD文件
  使用: epub_converter
  输入: book.epub
  输出: book/01_xxx.md, 02_xxx.md, ...

场景2: 长文本小说 → MD文件
  使用: text_splitter
  输入: novel.txt
  输出: novel/01_xxx.md, 02_xxx.md, ...

场景3: 长文本 → EPUB → MD
  使用: 先用其他工具转为EPUB，再用epub_converter
```

---

## 8. 实施计划

### 阶段1: 核心功能 (第1-2天)

- [x] 创建项目结构
- [ ] 实现file_reader.py（支持txt, md）
- [ ] 实现chapter_detector.py（基本模式）
- [ ] 实现content_splitter.py
- [ ] 实现file_manager.py
- [ ] 实现main.py基础CLI
- [ ] 创建__init__.py和__main__.py

### 阶段2: 增强功能 (第3天)

- [ ] 实现docx格式支持（file_reader.py增强）
- [ ] 实现format_converter.py
- [ ] 完善章节检测模式
- [ ] 添加交互式确认
- [ ] 编写text_splitter.bat

### 阶段3: 优化测试 (第4天)

- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 创建测试样本文件
- [ ] 完善错误处理
- [ ] 编写README.md
- [ ] 创建setup.py

---

## 9. 测试策略

### 单元测试

```
tests/
├── test_file_reader.py
│   ├── test_read_txt_file()
│   ├── test_read_md_file()
│   └── test_detect_encoding()
│
├── test_chapter_detector.py
│   ├── test_detect_chinese_chapters()
│   ├── test_detect_english_chapters()
│   ├── test_detect_episodes()
│   └── test_filter_short_chapters()
│
├── test_content_splitter.py
│   ├── test_split_content()
│   └── test_handle_edge_cases()
│
└── test_file_manager.py
    ├── test_sanitize_filename()
    ├── test_generate_filename()
    └── test_save_chapters()
```

### 集成测试

```
tests/test_integration.py
├── test_full_workflow_txt()
├── test_full_workflow_docx()
└── test_batch_processing()
```

### 测试样本

```
tests/sample_files/
├── novel.txt              # 纯文本小说
├── novel_with_headers.md  # 带标题的MD
├── novel.docx             # Word文档
└── novel_complex.txt      # 复杂格式（混合章节标记）
```

---

## 10. 错误处理

### 文件读取错误

- 文件不存在 → 提示重新输入
- 编码错误 → 尝试多种编码
- 格式不支持 → 显示支持的格式列表

### 章节检测错误

- 未检测到章节 → 询问是否作为单文件输出
- 检测到过多章节 → 提示可能误识别，显示预览
- 章节内容过短 → 自动过滤

### 文件保存错误

- 输出目录无权限 → 提示更改目录
- 文件名冲突 → 自动重命名（添加后缀）
- 磁盘空间不足 → 提示清理空间

---

## 11. 性能考虑

### 大文件处理

- 流式读取txt文件（不一次性加载全部内容）
- 按需处理docx段落
- 进度显示（每处理N行显示一次）

### 内存优化

- 及时释放已处理的文件对象
- 使用生成器而非列表处理大文件

---

## 12. 未来扩展

### 可能的增强功能

- [ ] 支持更多格式（PDF, HTML, RTF）
- [ ] 自定义章节模式配置文件
- [ ] 批量处理文件夹
- [ ] GUI界面
- [ ] 输出合并的单个MD文件
- [ ] 保留图片并转换为Markdown链接
- [ ] 自动识别并移除页眉页脚
- [ ] 智能合并过短章节

---

## 版本历史

### v1.0.0 (2025-12-31)

- 初始版本
- 支持txt, md, docx格式
- 基本章节检测
- 与epub_converter输出格式对齐

---

**文档版本**: 1.0
**最后更新**: 2025-12-31
**维护者**: Claude Code
