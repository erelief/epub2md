# epub2md

将 EPUB 电子书转换为结构化的 Markdown 文件，**精确还原书中的脚注和注释**。

大多数 EPUB 转 Markdown 工具在转换时会丢失或破坏注释——要么注释标记变成死链接，要么注释内容被丢弃。epub2md 专门解决了这个问题：它能识别 EPUB 中的脚注/尾注结构，将注释标记与注释内容正确配对，并支持两种还原模式（内联或页内跳转）。

## 功能特性

### 注释还原（核心功能）

EPUB 中的注释通常以跨页超链接的形式存在：正文中的上标数字链接到另一个页面的注释内容，注释内容又有返回链接。epub2md 实现了完整的注释处理流程：

- **自动识别注释结构** — 通过关键词搜索 + href/id 配对算法，准确找到注释标记（A）和注释内容（B）的对应关系，支持同页注释和跨页注释
- **图片标记转换** — 部分 EPUB 使用小图片作为注释标记（如注、编号图标），自动将其转换为文本标记 `[1]` `[2]`
- **两种还原模式**：
  - **内联注释模式** — 将注释内容直接插入到正文引用处，格式为 `（注：注释内容）`，阅读时无需跳转
  - **页内跳转模式** — 跨页注释自动迁移到引用所在页面底部，保留双向跳转链接（`[1](#note-1)` ↔ `[^](#back-1)`），还原原书的注释阅读体验
- **中英文自动适配** — 中文书籍使用 `（注：...）` 格式，英文书籍使用 `(Note: ...)` 格式
- **载体图片排除** — 注释标记用的小图片不会作为内容图片被提取

### 内容转换

- **EPUB 解析** — 提取元数据（书名、作者等）、目录结构、内容文件
- **HTML → Markdown** — 将 EPUB 内部的 HTML/XHTML 内容转换为干净的 Markdown，处理 CSS 样式、嵌套格式标签、HTML 实体等
- **文件重命名** — 将 EPUB 内部的 `text00001.html` 等文件名重命名为可读的 `01_章节名.md`
- **跨页链接修正** — 自动更新所有文件间引用，确保转换后的 Markdown 链接仍然有效
- **封面提取** — 自动提取封面图片，不生成多余的封面 Markdown 文件
- **图片管理** — 提取所有内容图片，更新 Markdown 中的图片引用路径
- **标题页智能合并** — 检测仅含标题的短页面，交互式询问是否与下一页合并
- **语言检测** — 自动检测中文/英文内容，适配注释格式
- **自动生成合并版** — 转换完成后自动生成一个包含所有章节的完整 Markdown 文件

### 批量处理

- 支持转换单个 EPUB 文件或整个文件夹中的所有 EPUB
- 支持命令行参数和交互式两种使用方式

## 安装

### 便携版（推荐，无需安装 Python）

1. 前往 [Releases](https://github.com/erelief/epub2md/releases) 页面下载最新版本的 `epub2md-x.x.x-portable.zip`
2. 解压到任意目录
3. 双击 `epub_converter.bat` 或 `merge_md.bat` 即可使用

便携版内置了 Python 运行环境和所有依赖，解压即用。

### 从源码运行

如果已有 Python 环境，也可以直接克隆运行：

```bash
git clone https://github.com/erelief/epub2md.git
cd epub2md
pip install html2text
```

## 使用方法

### epub_converter.bat（主程序）

双击 `epub_converter.bat` 或在命令行运行：

```batch
epub_converter.bat
```

也支持命令行直接指定文件：

```batch
# 转换单个文件
epub_converter.bat book.epub

# 批量转换文件夹中的所有 EPUB
epub_converter.bat C:\Books\epub_folder

# 指定输出目录
epub_converter.bat -o C:\Output book.epub

# 指定注释处理模式（跳过交互选择）
epub_converter.bat -a inline book.epub     # 内联注释
epub_converter.bat -a jump book.epub       # 页内跳转
```

**使用流程**：

1. 运行脚本，输入 EPUB 文件路径（支持拖拽文件到窗口）
2. 选择注释处理模式（内联注释 / 页内跳转）
3. 如果检测到疑似标题页，选择是否合并到下一章
4. 转换完成后，在 EPUB 同目录下的同名文件夹中查看结果
5. 脚本会询问是否继续转换其他文件

**输出结构**：

```
book_name/
├── 01_第一章_标题.md
├── 02_第二章_标题.md
├── ...
├── book_name.md          ← 自动生成的完整合并版
├── images/
│   ├── image001.png
│   └── ...
└── cover.jpg             ← 封面图片
```

### merge_md.bat（辅助工具）

将一个目录中的多个 Markdown 文件合并为一个完整文件，并自动修正跨页链接和锚点。

```batch
merge_md.bat
```

运行后输入包含 Markdown 文件的目录路径即可。合并工具会：

- 为每个锚点 ID 添加页码前缀，避免合并后 ID 冲突
- 修正所有跨页链接的目标锚点
- 修正同页链接的锚点引用
- 移除链接中的 `.md` 文件名，统一为页内锚点格式

## 命令行参数

```
python -m epub_converter [文件或文件夹路径] [选项]

参数：
  epub_file              EPUB 文件路径或包含 EPUB 的文件夹路径

选项：
  -o, --output DIR       指定输出目录
  -a, --annotation-mode  注释处理模式: inline（内联）或 jump（页内跳转）
  -v, --verbose          显示详细处理信息
  --version              显示版本号
```

## 项目结构

```
epub2md/
├── .github/workflows/
│   └── build-release.yml    # CI: 自动构建便携版 Release
├── epub_converter.bat       # 主程序启动脚本
├── merge_md.bat             # MD 合并工具启动脚本
├── epub_converter/          # 转换器核心模块
│   ├── main.py              # 主入口和 CLI
│   ├── epub_parser.py       # EPUB 文件解析
│   ├── content_processor.py # HTML → Markdown 转换
│   ├── annotation_processor.py  # 注释/脚注处理（核心）
│   ├── link_processor.py    # 链接引用修正
│   ├── file_manager.py      # 文件重命名管理
│   ├── image_handler.py     # 图片提取和链接更新
│   ├── cover_handler.py     # 封面处理
│   ├── language_detector.py # 语言检测
│   ├── merged_output_generator.py  # 合并版 MD 生成
│   └── utils.py             # 工具函数
├── md_merger/               # MD 合并工具模块
│   └── core.py              # 合并和链接修正逻辑
└── requirements.txt         # Python 依赖
```

## 许可证

MIT License
