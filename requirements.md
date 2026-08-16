### Word格式批量处理在线编辑器 · AI开发指令文档 v3.0

> **文档用途**：本文档专为AI编程助手（Codex/Cursor/Copilot等）设计。所有需求已转化为可执行的工程指令、明确的技术约束和可验证的验收条件。消除自然语言歧义，采用结构化数据定义。
>
> **部署目标**：Windows单文件/免安装运行，解压即用。

---

## 1. 项目元信息

```yaml
project_name: word-format-batch-editor
version: 1.0.0
python_version: ">=3.11,<3.13"
license: MIT
description: Web-based batch Word document format processor with structure-aware editing
deployment_target: Windows standalone portable (no install required)
ai_codex_instructions: true
```

---

## 2. 技术栈约束（强制）

AI生成代码时**必须**使用以下指定技术，不得自行替换：

| 层级 | 技术 | 版本约束 | 用途 |
|------|------|----------|------|
| 后端框架 | FastAPI | >=0.110,<1.0 | HTTP API + WebSocket |
| 异步任务 | Celery | >=5.3,<6.0 | 批量处理任务队列 |
| 消息代理 | Redis | 嵌入式(redis-server.exe) | Celery broker + 缓存 |
| 数据库 | SQLite | stdlib | 配置/日志/模板存储 |
| ORM | SQLAlchemy | >=2.0,<3.0 | 数据访问层 |
| Word解析 | python-docx | >=1.1,<2.0 | .docx读写基础 |
| XML操作 | lxml | >=5.0,<6.0 | OOXML底层操作兜底 |
| 前端框架 | Vue 3 | ^3.4 | SPA |
| UI组件库 | Element Plus | ^2.7 | 表单/表格/对话框 |
| 构建工具 | Vite | ^5.0 | 前端构建 |
| 状态管理 | Pinia | ^2.1 | 全局状态 |
| HTTP客户端 | Axios | ^1.7 | API调用 |
| WS客户端 | socket.io-client | ^4.7 | 实时进度/日志 |
| 打包工具 | PyInstaller | >=6.0 | Windows单目录打包 |
| 前端嵌入 | vite-plugin-singlefile | ^2.0 | 前端打包为单HTML嵌入后端 |
| 日志 | loguru | >=0.7 | 结构化日志 |
| 数据校验 | Pydantic | >=2.0,<3.0 | 请求/响应模型 |

---

## 3. Windows便携部署架构（核心约束）

### 3.1 最终交付物结构

AI生成的项目**必须**能构建出以下目录结构，用户解压后双击`start.bat`即可运行：

```
WordFormatEditor/                  # 解压根目录
├── start.bat                      # 一键启动脚本
├── stop.bat                       # 一键停止脚本
├── config.yaml                    # 用户可编辑配置文件
├── logs/                          # 运行日志目录（自动创建）
├── data/                          # SQLite数据库（自动创建）
├── storage/                       # 文件存储目录（自动创建）
│   ├── original/                  # 原始上传文件
│   ├── processed/                 # 处理后文件
│   ├── snapshots/                 # 回滚快照
│   └── temp/                      # 临时文件
├── backend/                       # Python后端（PyInstaller打包）
│   ├── server.exe                 # FastAPI主服务
│   ├── worker.exe                 # Celery Worker
│   └── _internal/                 # Python运行时+依赖
├── redis/                         # 嵌入式Redis
│   ├── redis-server.exe           # Redis服务端（Windows版）
│   └── redis.conf                 # Redis配置
└── frontend/                      # 前端静态文件（可选，已嵌入backend）
    └── index.html                 # 单文件前端（备用）
```

### 3.2 start.bat 规范

```batch
@echo off
chcp 65001 >nul
title Word Format Batch Editor v1.0

:: 检查端口占用
netstat -ano | findstr ":8000" >nul && (
    echo [ERROR] Port 8000 is already in use. Please close other programs or edit config.yaml.
    pause
    exit /b 1
)

:: 启动Redis
echo [INFO] Starting Redis...
start /min "" "%~dp0redis\redis-server.exe" "%~dp0redis\redis.conf"
timeout /t 2 /nobreak >nul

:: 启动Celery Worker
echo [INFO] Starting Celery Worker...
start /min "" "%~dp0backend\worker.exe" --pool=solo --loglevel=info

:: 启动FastAPI Server
echo [INFO] Starting Web Server...
start /min "" "%~dp0backend\server.exe"

:: 等待服务就绪并打开浏览器
echo [INFO] Waiting for server to be ready...
:wait_loop
curl -s http://localhost:8000/api/v1/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo [INFO] Server is ready! Opening browser...
start http://localhost:8000
echo.
echo ========================================
echo   Word Format Batch Editor is running
echo   URL: http://localhost:8000
echo   Press Ctrl+C or run stop.bat to stop
echo ========================================
pause
```

### 3.3 stop.bat 规范

```batch
@echo off
chcp 65001 >nul
echo [INFO] Stopping Word Format Batch Editor...

:: 停止FastAPI
taskkill /f /im server.exe >nul 2>&1
:: 停止Celery Worker
taskkill /f /im worker.exe >nul 2>&1
:: 停止Redis
taskkill /f /im redis-server.exe >nul 2>&1

echo [INFO] All services stopped.
pause
```

### 3.4 config.yaml 规范

```yaml
# Word Format Batch Editor Configuration
server:
  host: "0.0.0.0"
  port: 8000
  workers: 1  # Uvicorn workers, keep 1 for SQLite compatibility

celery:
  concurrency: 4  # Number of parallel document processing workers
  broker_url: "redis://localhost:6379/0"
  result_backend: "redis://localhost:6379/1"

storage:
  base_path: "./storage"       # Relative to start.bat location
  max_file_size_mb: 100        # Single file upload limit
  max_batch_size: 500          # Max files per batch
  temp_retention_hours: 24     # Auto-cleanup temp files
  original_retention_days: 30  # Keep original files

database:
  url: "sqlite:///./data/app.db"

security:
  jwt_secret: "CHANGE_ME_TO_RANDOM_STRING"  # Auto-generated on first run if empty
  jwt_expire_minutes: 1440
  cors_origins: ["http://localhost:8000"]

logging:
  level: "INFO"                # TRACE/DEBUG/INFO/WARN/ERROR/FATAL
  file: "./logs/app.log"
  max_size_mb: 50
  backup_count: 10

preview:
  refresh_debounce_ms: 150     # Preview update debounce
  max_render_pages: 50         # Max pages to render in preview
```

### 3.5 PyInstaller打包指令

AI必须在项目中包含以下构建脚本`build_windows.bat`：

```batch
@echo off
echo === Building Frontend ===
cd frontend
call npm ci
call npm run build
cd ..

echo === Building Backend Server ===
pyinstaller --noconfirm --onedir --name server ^
  --add-data "frontend/dist;frontend/dist" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  backend/main.py

echo === Building Celery Worker ===
pyinstaller --noconfirm --onedir --name worker ^
  --hidden-import celery ^
  --hidden-import celery.concurrency.solo ^
  backend/worker_entry.py

echo === Packaging Redis ===
mkdir dist\WordFormatEditor\redis
copy redis-windows\redis-server.exe dist\WordFormatEditor\redis\
copy redis-windows\redis.conf dist\WordFormatEditor\redis\

echo === Copying Config & Scripts ===
copy config.yaml dist\WordFormatEditor\
copy start.bat dist\WordFormatEditor\
copy stop.bat dist\WordFormatEditor\

echo === Build Complete ===
echo Output: dist\WordFormatEditor\
```

---

## 4. 后端工程结构（AI必须遵循）

```
backend/
├── main.py                 # FastAPI入口，挂载路由+静态文件+WS
├── worker_entry.py         # Celery Worker入口
├── config.py               # 读取config.yaml，Pydantic Settings
├── database.py             # SQLAlchemy engine/session/Base
├── dependencies.py         # FastAPI依赖注入（auth, db session）
│
├── models/                 # SQLAlchemy ORM模型
│   ├── __init__.py
│   ├── user.py
│   ├── document.py
│   ├── template.py
│   ├── task.py
│   └── log_entry.py
│
├── schemas/                # Pydantic请求/响应模型
│   ├── __init__.py
│   ├── document.py
│   ├── format_spec.py      # FormatSpec/NumberingSpec/TableFormatSpec
│   ├── template.py
│   ├── task.py
│   ├── rule.py             # FormatRule条件+动作模型
│   └── response.py         # 统一响应包装
│
├── api/                    # API路由
│   ├── __init__.py
│   ├── router.py           # 汇总所有子路由
│   ├── auth.py             # POST /login, /refresh
│   ├── documents.py        # CRUD + upload + structure + preview
│   ├── templates.py        # CRUD
│   ├── tasks.py            # create/dry-run/pause/resume/cancel/results/diff/rollback
│   ├── rules.py            # validate/test
│   ├── logs.py             # query/export
│   └── ws.py               # WebSocket progress/logs
│
├── services/               # 业务逻辑层
│   ├── __init__.py
│   ├── document_service.py
│   ├── format_engine.py    # 核心：格式应用引擎
│   ├── structure_parser.py # 核心：文档结构解析
│   ├── numbering_engine.py # 核心：编号样式处理
│   ├── template_service.py
│   ├── task_service.py
│   ├── rule_engine.py      # 规则匹配引擎
│   └── diff_service.py     # Diff对比生成
│
├── core/                   # 底层OOXML操作
│   ├── __init__.py
│   ├── ooxml_reader.py     # ZIP解压+XML读取
│   ├── ooxml_writer.py     # XML修改+ZIP重打包
│   ├── styles_parser.py    # styles.xml解析
│   ├── numbering_parser.py # numbering.xml解析
│   └── html_renderer.py    # docx→HTML预览渲染
│
├── tasks/                  # Celery任务定义
│   ├── __init__.py
│   └── process_task.py     # 单文档处理任务
│
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── file_utils.py       # SHA256/魔数校验/路径安全
│   ├── zip_validator.py    # .docx ZIP完整性校验
│   └── logger.py           # loguru配置
│
└── tests/                  # pytest测试
    ├── conftest.py
    ├── test_structure_parser.py
    ├── test_format_engine.py
    ├── test_numbering_engine.py
    ├── test_rule_engine.py
    ├── test_api_documents.py
    ├── test_api_tasks.py
    └── fixtures/           # 测试用.docx文件
        ├── simple.docx
        ├── headings_multi.docx
        ├── tables_complex.docx
        ├── lists_mixed.docx
        ├── encrypted.docx
        └── corrupted.docx
```

---

## 5. 核心模块实现指令

### 5.1 文档结构解析器 (`structure_parser.py`)

**输入**：`.docx`文件路径
**输出**：`DocumentStructure` Pydantic模型

```python
# AI必须实现的解析逻辑：
class DocumentNode(BaseModel):
    id: str                          # UUID
    type: Literal["heading","paragraph","table","list_item","image","page_break","section_break"]
    level: int = 0                   # heading level / list indent level
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    section_id: str                  # 所属章节ID
    content_preview: str             # 前50字符
    style_name: str                  # 原始w:pStyle值
    xml_xpath: str                   # 在document.xml中的XPath
    current_format: FormatSpec       # 当前直接格式快照
    table_info: Optional[TableInfo]  # 仅type=table时有值

class TableInfo(BaseModel):
    rows: int
    cols: int
    merged_cells: List[MergedCell]   # [{row,col,row_span,col_span}]
    nested_tables: List[str]         # 嵌套表格的node_id列表
    has_header_row: bool

class DocumentStructure(BaseModel):
    document_id: str
    total_pages: int
    sections: List[SectionInfo]      # 章节层级树
    nodes: Dict[str, DocumentNode]   # node_id → node映射
    root_node_ids: List[str]         # 顶层节点ID列表
    statistics: StructureStats       # {heading_count, paragraph_count, table_count, ...}
```

**解析规则（AI必须遵守）**：
1. 标题识别：优先读`<w:outlineLvl>`，其次读`<w:pStyle>`匹配`Heading1-9`或自定义标题样式名
2. 列表识别：解析`<w:numPr><w:numId>`关联`numbering.xml`，通过`<w:ilvl>`确定层级
3. 表格识别：遍历`<w:tbl>`，解析`<w:gridCol>`获取列数，`<w:gridSpan>`和`<w:vMerge>`识别合并
4. 嵌套表格：`<w:tc>`内包含`<w:tbl>`时递归解析，parent_id指向外层表格节点
5. 章节归属：每个非标题节点向上查找最近的祖先heading节点作为section_id
6. 页眉页脚：单独解析`header*.xml`/`footer*.xml`，不作为正文结构树节点，但记录关联section

### 5.2 格式应用引擎 (`format_engine.py`)

**输入**：`.docx`文件路径 + `List[FormatRule]` + `Optional[TemplateConfig]`
**输出**：处理后`.docx`文件路径 + `List[Modification]`

**优先级规则（AI必须按此顺序应用）**：
```
1. 局部手动覆盖（用户在UI中对特定节点设置的格式）
2. 自定义规则（按rule.priority降序）
3. 模板配置
4. 全局默认配置
5. 文档原始样式（不修改）
```

**FormatRule数据模型**：
```python
class RuleCondition(BaseModel):
    node_type: Optional[Literal["heading","paragraph","table","list_item"]] = None
    level: Optional[int] = None              # heading level / list level
    style_name_contains: Optional[str] = None
    content_contains: Optional[str] = None
    section_title_contains: Optional[str] = None
    table_min_rows: Optional[int] = None
    table_max_rows: Optional[int] = None
    custom_expression: Optional[str] = None  # Python eval安全沙箱表达式

class RuleAction(BaseModel):
    font_cn: Optional[str] = None
    font_en: Optional[str] = None
    font_size: Optional[float] = None
    font_color: Optional[str] = None         # HEX "#RRGGBB"
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[str] = None          # "single"/"double"/"wave"/None
    alignment: Optional[str] = None          # "left"/"center"/"right"/"justify"/"distribute"
    line_spacing: Optional[float] = None     # 倍数或固定值pt
    space_before: Optional[float] = None     # pt
    space_after: Optional[float] = None      # pt
    first_line_indent: Optional[float] = None # pt
    numbering: Optional[NumberingSpec] = None
    table_format: Optional[TableFormatSpec] = None

class FormatRule(BaseModel):
    id: str
    name: str
    priority: int                            # 数字越大优先级越高
    enabled: bool = True
    condition: RuleCondition
    action: RuleAction
```

**AI实现要求**：
- 每次格式修改必须记录`Modification(before_value, after_value, rule_id, node_path, timestamp)`
- 修改通过lxml直接操作XML节点，不依赖python-docx的高层API（避免丢失不支持的属性）
- 处理完成后重新打包ZIP，保留原始`[Content_Types].xml`和关系文件中未修改的部分
- 加密文档检测：尝试解压时捕获异常，返回`SKIPPED`状态+原因

### 5.3 编号引擎 (`numbering_engine.py`)

**AI必须实现的编号处理逻辑**：
1. 解析`word/numbering.xml`中所有`<w:abstractNum>`和`<w:num>`定义
2. 建立`numId → abstractNumId → levels[]`完整映射
3. 修改编号样式时：
   - 若目标编号格式已存在于`abstractNum`中，直接引用
   - 若不存在，创建新的`abstractNum`条目并关联
4. 支持的多级格式模板变量：`{1}`=级别1编号, `{2}`=级别2编号, ..., `{upper_1}`=大写级别1
5. 编号字体/字号/颜色通过`<w:rPr>`在`<w:lvl>`的`<w:start>`同级设置
6. 缩进通过`<w:pPr><w:ind w:left="..." w:hanging="..."/>`设置

### 5.4 规则引擎 (`rule_engine.py`)

**AI必须实现**：
- 条件匹配：对每个`DocumentNode`逐条评估`FormatRule.condition`
- `custom_expression`安全执行：仅允许访问节点属性（type, level, style_name, content_preview, section_title, table_rows），禁止import/os/sys等危险操作
- 使用`ast.literal_eval`或受限`eval`沙箱
- 返回匹配的规则列表（按priority排序），取最高优先级规则的action应用

### 5.5 HTML预览渲染器 (`html_renderer.py`)

**AI必须实现**：
- 将`DocumentStructure` + 当前格式配置渲染为HTML字符串
- 支持实时刷新：接收增量格式变更，仅重新渲染受影响节点
- CSS内联到style属性，确保单HTML文件可独立显示
- 表格渲染保留合并单元格（colspan/rowspan）
- 图片以base64嵌入或占位符显示
- 最大渲染页数限制（config.preview.max_render_pages）

---

## 6. API接口契约（OpenAPI 3.0兼容）

AI生成的所有API**必须**符合以下契约，不得增减字段：

### 6.1 统一响应格式

```json
{
  "code": 0,           // 0=成功, 非0=错误码
  "message": "success",
  "data": {}           // 业务数据，失败时为null
}
```

### 6.2 核心端点清单

| Method | Path | Request Body | Response Data | Notes |
|--------|------|-------------|---------------|-------|
| POST | `/api/v1/auth/login` | `{username,password}` | `{access_token,refresh_token,expires_in}` | |
| POST | `/api/v1/auth/refresh` | `{refresh_token}` | `{access_token,expires_in}` | |
| POST | `/api/v1/documents/upload` | multipart/form-data | `{id,name,size,pages,status}` | 支持多文件 |
| GET | `/api/v1/documents` | query: page,size,sort,status,tag | `{items[],total,page,size}` | |
| GET | `/api/v1/documents/{id}/structure` | - | `DocumentStructure` | |
| GET | `/api/v1/documents/{id}/preview` | query: page,zoom | `{html,total_pages}` | |
| POST | `/api/v1/templates` | `TemplateCreate` | `Template` | |
| GET | `/api/v1/templates` | - | `Template[]` | |
| PUT | `/api/v1/templates/{id}` | `TemplateUpdate` | `Template` | |
| DELETE | `/api/v1/templates/{id}` | - | `{deleted:true}` | |
| POST | `/api/v1/rules/validate` | `FormatRule` | `{valid,errors[]}` | |
| POST | `/api/v1/rules/test` | `{rule,node_snapshot}` | `{matched,applied_action}` | |
| POST | `/api/v1/tasks/dry-run` | `TaskCreate` | `DryRunReport` | |
| POST | `/api/v1/tasks` | `TaskCreate` | `{task_id,status,total,estimated_seconds}` | |
| GET | `/api/v1/tasks/{id}` | - | `TaskStatus` | |
| PUT | `/api/v1/tasks/{id}/pause` | - | `{status:"PAUSED"}` | |
| PUT | `/api/v1/tasks/{id}/resume` | - | `{status:"RUNNING"}` | |
| DELETE | `/api/v1/tasks/{id}` | - | `{status:"CANCELLED"}` | |
| GET | `/api/v1/tasks/{id}/results` | - | `ProcessResult[]` | |
| GET | `/api/v1/tasks/{id}/diff` | - | `DiffReport` | |
| POST | `/api/v1/tasks/{id}/rollback` | `{node_ids[]?}` | `{rolled_back_count}` | 空数组=全部回滚 |
| GET | `/api/v1/logs` | query: level,document,action,from,to,page,size | `{items[],total}` | |
| GET | `/api/v1/logs/export` | query: format(log/json/csv),filters | File download | |
| POST | `/api/v1/documents/{id}/download` | - | File download (.docx) | |
| POST | `/api/v1/documents/batch-download` | `{document_ids[]}` | File download (.zip) | |
| GET | `/api/v1/health` | - | `{status:"ok",version,uptime}` | 健康检查 |
| WS | `/ws/v1/progress?task_id=` | - | `{task_id,progress,current_doc,status}` | |
| WS | `/ws/v1/logs` | - | `LogEntry` | 实时日志流 |

---

## 7. 前端工程约束

### 7.1 构建产物要求

- `npm run build` 必须输出**单个`index.html`文件**（含内联CSS/JS）
- 使用`vite-plugin-singlefile`插件
- 后端通过FastAPI `StaticFiles`或直接读取该HTML文件提供服务
- 前端不依赖任何外部CDN资源（离线可用）

### 7.2 页面路由

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | Dashboard | 概览统计 |
| `/documents` | DocumentList | 文档管理 |
| `/editor/:docId` | Editor | 结构树+配置+预览三栏 |
| `/tasks` | TaskList | 批量任务管理 |
| `/tasks/:taskId` | TaskDetail | 任务详情+进度+结果 |
| `/templates` | TemplateManager | 模板CRUD |
| `/logs` | LogViewer | 日志查询+Debug面板 |
| `/settings` | Settings | 系统配置 |

### 7.3 编辑器页面布局（三栏）

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar: [保存配置] [Dry-Run] [执行处理] [撤销] [快捷键帮助] │
├──────────┬──────────────────────────────┬───────────────────┤
│ 结构树    │     预览区 / Diff视图        │  属性配置面板     │
│ 240px    │     flex: 1                  │  320px            │
│ 可折叠    │     缩放/翻页/标尺           │  可折叠           │
│ 搜索/筛选 │                              │  上下文感知       │
│ 右键菜单  │                              │  规则编辑器       │
├──────────┴──────────────────────────────┴───────────────────┤
│ Status Bar: 当前节点信息 | 配置来源 | 缩放 | Debug Toggle   │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 测试要求（AI必须生成）

### 8.1 单元测试覆盖率目标

| 模块 | 最低覆盖率 | 关键测试点 |
|------|-----------|-----------|
| structure_parser | 90% | 多级标题/嵌套表格/合并单元格/混合列表/加密文档/损坏文档 |
| format_engine | 90% | 优先级覆盖/格式记录/ZIP重打包/大文件流式处理 |
| numbering_engine | 85% | 多级编号/格式模板变量/缩进/字体独立设置 |
| rule_engine | 90% | 条件组合/安全沙箱/优先级排序/边界值 |
| html_renderer | 80% | 表格合并/图片占位/增量更新/页数限制 |

### 8.2 测试fixture文件

AI必须在`backend/tests/fixtures/`下生成或提供以下测试文档的创建脚本：

| 文件名 | 内容要求 |
|--------|----------|
| `simple.docx` | 10段纯正文，无特殊格式 |
| `headings_multi.docx` | Heading1-9各1个，嵌套3层 |
| `tables_complex.docx` | 含合并单元格+嵌套表格+跨页表格 |
| `lists_mixed.docx` | 有序+无序+9级嵌套混合列表 |
| `numbering_complex.docx` | 章节编号+图表编号+列表编号混合 |
| `encrypted.docx` | 密码保护（密码：test123） |
| `corrupted.docx` | 截断的无效ZIP文件 |
| `custom_styles.docx` | 5个自定义样式名 |

---

## 9. 验收检查清单（AI自检）

AI完成开发后，必须逐项确认以下条件全部满足：

- [ ] `build_windows.bat`执行无报错，产出`dist/WordFormatEditor/`目录
- [ ] `start.bat`双击后浏览器自动打开`http://localhost:8000`且页面正常加载
- [ ] `stop.bat`双击后所有进程（server.exe/worker.exe/redis-server.exe）均终止
- [ ] 上传`.docx`文件后结构树正确展示标题/段落/表格/列表
- [ ] 修改字体/字号/颜色后预览区≤300ms刷新
- [ ] 批量处理10份文档全部成功，下载ZIP包含所有处理后文件
- [ ] Dry-Run不修改任何文件，报告内容与正式处理一致
- [ ] 操作日志记录每条修改的before/after值
- [ ] 撤销操作后文档格式恢复
- [ ] 上传损坏文件时标记FATAL并跳过，不影响其他文件
- [ ] 上传加密文件时提示输入密码或跳过
- [ ] 所有API返回统一响应格式`{code,message,data}`
- [ ] 前端无外部CDN依赖，离线环境可正常使用
- [ ] pytest全部通过，覆盖率达标
- [ ] config.yaml修改后重启生效

---

## 10. AI开发顺序建议

按以下顺序逐步实现，每步完成后运行测试验证：

```
Phase 1: 基础骨架 (Day 1-2)
  ├── 项目结构初始化 + config.yaml读取
  ├── SQLite数据库模型 + migration
  ├── FastAPI入口 + health端点
  ├── 前端Vue3脚手架 + 单文件构建
  └── start.bat/stop.bat + Redis集成

Phase 2: 文档上传与解析 (Day 3-5)
  ├── 文件上传API + 校验 + 存储
  ├── structure_parser实现 + 单元测试
  ├── 结构树API + 前端结构树组件
  └── HTML预览渲染器 + 前端预览组件

Phase 3: 格式引擎 (Day 6-9)
  ├── FormatSpec/Rule数据模型
  ├── format_engine核心实现 + 单元测试
  ├── numbering_engine实现 + 单元测试
  ├── rule_engine实现 + 单元测试
  └── 前端配置面板 + 实时预览联动

Phase 4: 批量处理 (Day 10-12)
  ├── Celery任务定义 + Worker入口
  ├── 任务API（create/pause/resume/cancel）
  ├── WebSocket进度推送
  ├── Dry-Run实现
  └── 前端任务管理页面

Phase 5: 模板/Diff/回滚 (Day 13-15)
  ├── 模板CRUD API + 前端
  ├── Diff对比服务 + 前端Diff视图
  ├── 操作日志系统 + 前端日志面板
  ├── 回滚机制
  └── 规则测试/验证API

Phase 6: 打包与验收 (Day 16-17)
  ├── PyInstaller打包脚本
  ├── Windows便携包集成测试
  ├── E2E测试（Playwright）
  ├── 性能测试
  └── 验收检查清单逐项确认
```

---

> **给AI的最终指令**：严格按照本文档的技术栈、工程结构、数据模型、API契约和部署架构生成代码。不要引入文档未指定的依赖。不要简化或省略任何模块。每个核心模块必须有对应的单元测试。最终交付物必须是Windows下解压即用的便携包。