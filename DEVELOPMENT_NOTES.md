# Word Format Batch Editor — 开发记忆文档

> **版本**：v4（2026-08-15）
> **读者**：接手本项目的 AI / 开发者
> **配套文档**：`requirements.md`（原始需求）、`PHASE_REPORT_V2.md`（阶段报告）、`AI_Coding_Guidelines.md`（硬性规则）、`.workbuddy/memory/2026-08-15.md`（八轮迭代日志）

---

## 1. 项目概述

Web 版 Word 文档批量格式处理器。上传 .docx → 解析结构树 → 可视化编辑格式 → 保存为模板 → 批量套用到多个文档 → 下载结果。Windows 便携部署，完全离线运行。

**技术栈**：FastAPI + Celery + Redis + SQLite + lxml（后端）；Vue 3 + Element Plus + Vite 单文件构建（前端）。

**参考文档**：42MB《深信服超融合HCI6120技术白皮书.docx》（5101 结构节点、477 目录条目、504 张图片、14719 处修订标记），是所有性能与兼容性优化的基准。

---

## 2. 架构地图

```
backend/
├── main.py                  # FastAPI 入口：路由 + 静态前端 + WS + lifespan
├── config.py                # config.yaml → Pydantic Settings（单例 get_config）
├── database.py              # SQLAlchemy engine/session，init_db() 建表
├── api/
│   ├── documents.py         # 上传/列表/structure/preview/media/下载/批量下载
│   ├── tasks.py             # dry-run/创建/暂停/恢复/取消/结果/diff/回滚
│   ├── templates.py / rules.py / logs.py / config.py / auth.py / ws.py
│   └── router.py            # 汇总，前缀 /api/v1
├── services/
│   ├── structure_parser.py  # 核心：docx → DocumentStructure（结构树）
│   ├── format_engine.py     # 核心：规则 → XML 修改 → 重打包
│   ├── numbering_engine.py  # 核心：numbering.xml 修改（多级编号）
│   ├── rule_engine.py       # 规则匹配（AST 沙箱 custom_expression）
│   ├── document_service.py / task_service.py / template_service.py / diff_service.py
├── core/
│   ├── ooxml_reader.py      # ZIP 解包 + XML 缓存
│   ├── ooxml_writer.py      # XML 修改 + ZIP 重打包 + 单位换算
│   ├── styles_parser.py     # styles.xml 解析 + basedOn 样式链回溯
│   ├── numbering_parser.py  # numbering.xml 解析（abstractNum/num/lvlOverride）
│   └── html_renderer.py     # DocumentStructure → HTML 预览
├── tasks/process_task.py    # Celery 任务（也被 api/tasks.py 线程直接调用）
└── tests/                   # 42 个 pytest（41 通过 + 1 个原有隔离问题）

frontend/src/
├── App.vue                  # 顶栏导航（全部菜单带 title 提示）
├── api.js / ws.js           # axios 实例（统一响应解包）/ 原生 WebSocket 客户端
├── views/
│   ├── Dashboard.vue        # 概览统计
│   ├── DocumentList.vue     # 文档管理（大上传框 + 分页记忆 + 状态中文解释）
│   ├── Editor.vue           # 核心：三栏编辑器（结构树/预览/属性）1550+ 行
│   ├── TaskList.vue / TaskDetail.vue  # 批量任务管理/详情（WS 实时进度）
│   ├── TemplateManager.vue  # 模板 CRUD
│   ├── LogViewer.vue        # 日志（默认全量 + 级别/操作/文档/关键词筛选）
│   └── Settings.vue         # 系统设置（含主题切换）
└── dist/index.html          # 单文件构建产物（vite-plugin-singlefile）
```

**数据流**：上传 → `save_uploaded_file`（校验+快照）→ `/structure`（parse_document_structure_cached）→ 前端建树+预览 → 用户编辑（前端 current_format 即时预览）→ 保存规则/模板 → 创建任务 → `apply_format_rules`（lxml 改 XML）→ storage/processed/ → 下载。

---

## 3. 按模块开发报告

### 3.1 structure_parser.py（结构解析，最核心的模块）

**职责**：docx → DocumentStructure（nodes 字典 + root_node_ids 层级 + ordered_node_ids 文档顺序）。

**关键设计**：
- **确定性节点 ID**：`make_node_id()` 用递增序号 SHA-256 前 16 hex。同一文档两次解析 ID 完全一致（前端 /structure 与 /preview 两个接口靠此对齐）。**绝不允许改回 uuid4**。
- **标题识别三级兜底**：段落 `outlineLvl` → 样式链 `heading_level`（`_extract_heading_level` 支持 "S标题2"/"一级标题"/"1级标题" 等中文/WPS 变体）→ `resolve_style_chain` 沿 basedOn 回溯。
- **Track Changes**：`_extract_para_text` 递归遍历，取 `<w:ins>` 跳过 `<w:del>`，跳过 `<w:drawing>`/`<w:instrText>`。**这是预览空白的主要修复点，改动时务必保持递归**。
- **TOC 域状态机**（第八轮新增）：`toc_field_depth` 跟踪 fldChar begin/end。TOC 域第一个段落标 `content="__TOC__"`（渲染器自动生成目录），缓存条目段落（带编号+页码的静态文本）全部跳过，否则预览出现两份目录。`TOC \c/\a`（图表目录）整个丢弃。
- **编号文本模拟**（第八轮新增）：`num_counters` 按 numId 维护计数器，`compute_numbering_text` 格式化 lvlText 模板的 %N 占位符。段落级 numPr 优先，缺失时样式链回溯（SANGFOR 模板的标题编号在样式上）。Wingdings 私有区 bullet 字符（U+F000-F0FF）映射为真实 Unicode 符号。
- **图片节点**：段落含 `<a:blip>` 且是 paragraph → 转为 image 节点，content 存 media 文件名。
- **ordered_node_ids vs root_node_ids**：前者是文档顺序（渲染/format_engine 用），后者是层级顶层（树用）。format_engine 的 element 映射依赖文档顺序，两者不能互换。

### 3.2 format_engine.py（格式应用）

**职责**：规则 → lxml 修改 document.xml/numbering.xml → OOXMLWriter 重打包。

**关键设计**：
- `_build_element_node_map`：按文档顺序遍历 body 子元素，用 `next(node_iter)` 与 ordered_node_ids 一一配对。**段落顺序必须与 structure_parser 完全一致**，否则格式改错段落。
- 编号规则先统一处理（每个 (numId, ilvl) 只改一次 numbering.xml），再逐节点应用字体/段落属性。
- 每次修改记录 Modification（before/after），写入 LogEntry。
- **已知限制**：run 级格式只改第一个 `<w:r>` 的 rPr（多 run 段落的其余 run 不生效）。
- **回滚**：处理前快照到 storage/snapshots/，rollback 时复制回 original。

### 3.3 numbering_engine.py（编号引擎）

**关键设计**：
- `_level_text_for_ilvl`：多级格式按 ilvl 截取（'%1.%2.%3' 在 ilvl=1 → '%1.%2'），Word 才能自动续编。
- **NumberingSpec 扩展字段**（第八轮，向后兼容）：
  - `level_num_fmts: List[str]` — 每级独立 numFmt（如 L1 chineseCounting + L2-6 decimal）
  - `level_texts: List[str]` — 每级独立 lvlText（优先于截取；公文"一、/（一）/ 1. /（1）"靠它）
  - `legal_style: bool` — ilvl≥1 加 `<w:isLgl/>`，上级计数器强制十进制（"第一章 / 1.1"的关键）
- isLgl 用 `num_fmt.addnext()` 插入（OOXML w:lvl 元素顺序：start→numFmt→isLgl→lvlText）。

### 3.4 html_renderer.py（预览渲染）

**关键设计**：
- 按 ordered_node_ids 遍历；`content == "__TOC__"` → `_render_toc` 从标题节点生成锚点目录。
- 空段落用轻量 `<div class="empty-line">`（不重排）。
- 图片：`<img src="/api/v1/documents/{id}/media/{name}" loading="lazy" decoding="async">`。**不要 base64 内嵌**（504 张图会让 HTML 膨胀到 50MB+）。
- 编号前缀：`<span class="para-num">{numbering_text}</span>`。
- CSS 全部带 `.doc-preview` 前缀（v-html 注入的 style 是全局的，防止污染页面）。

### 3.5 media 端点（第八轮重写，性能关键）

`GET /documents/{id}/media/{name}`：
- **磁盘缓存**：`_ensure_media_extracted` 把 word/media/* 一次性解压到 `storage/temp/media_cache/{doc_id}/`（.done marker 记录源文件 mtime，变了自动重解压）。
- **immutable HTTP 缓存**：`Cache-Control: public, max-age=31536000, immutable`，浏览器滚动回访不再请求。
- preview 端点预热：渲染时预解压全部图片。

**为什么**：旧实现每个图片请求都打开 42MB zip 读中央目录。504 张图的懒加载请求占满 FastAPI 线程池（anyio 默认 40 线程），其他 API（/documents 列表）饿死十几秒超时——"浏览大文档后概览加载失败"的根因。

### 3.6 Editor.vue（前端核心，1550+ 行）

**性能关键设计（第七轮，实测验证）**：
- `previewIndex: Map<node_id, element>`：v-html 渲染后一次性建索引。所有 DOM 查找 O(1)。**禁止在大预览上 per-op querySelector**。
- `syncPreviewHighlight` 增量更新：lastHighlighted Set 差集操作，不全量遍历。
- `schedulePreviewStyle`：分块（600/帧）+ applyProgress 进度显示（状态栏）。新编辑到达时重启（写入幂等）。
- `watch(editableFormat, deep)` + 80ms 防抖 + `suppressFormatWatch` 标志（程序化赋值时阻断，微任务后释放）。
- el-tree 懒加载（`:lazy + loadTreeNode + isLeaf`）+ `setCheckedKeys` 批量勾选。**不要 setChecked 循环**。
- **预览节点无 CSS transition**（5000+ 节点的 hover/选中动画会让合成器持续繁忙，鼠标卡顿的主因）。
- `scrollIntoView` 用 `behavior: 'instant'`（smooth 在大文档上是长动画）。
- **window.xxx 代替 document.xxx**：Vue3 + vite minifier 会重命名 setup 作用域内裸 `document`（Bug #1 教训）。事件用 `window.addEventListener(..., true)` capture 委托。

**功能设计**：
- 选择模型：checkedNodes（多选）+ selectedNode（单选），activeNodes computed 统一（多选优先）。
- 双撤销栈：undoStack（选择）+ formatHistory（格式快照，上限 50）。
- computeSharedFormat：多选共同配置（全同显示，不同显示空白），标量快速路径 + 缓存 stringify。
- buildLayeredRules：模板按 L1-L6/正文/列表/表格/图片分层生成规则。
- NUMBERING_GROUPS：多级（至 L6）/单级/符号三组编号预设。

### 3.7 其他前端页面

- **DocumentList**：上传框 100% 宽 × 160px 高（wide-uploader）；分页 20/50/100/200 + localStorage 记忆（`doclist_page_size`）；状态中文 + tooltip 解释。
- **LogViewer**：默认全量；级别/操作（来自 /logs/actions distinct）/文档ID/关键词（后端 message LIKE）筛选。
- **TaskDetail**：WS 实时进度 + 5s 轮询兜底；结果表 checkbox + batch-download ZIP 下载。
- **App.vue**：所有导航菜单带 title 提示。

---

## 4. 开发坑点清单（按严重程度）

### P0 级（会导致功能完全失效）

1. **Vue3 + minifier + 裸 document**：setup 作用域内 `document.addEventListener` 会被压缩器重命名成局部变量导致委托失效。**必须 `window.document` / `window.addEventListener(..., true)`**。
2. **structure/preview 两次解析必须确定性 ID**：uuid4 会导致前端跨接口关联失败。用序号哈希。
3. **CSS Grid 三栏 + 2 个拖拽柄 = 5 列**：`grid-template-columns` 必须声明 5 列（240px 6px 1fr 6px 320px），否则第 4 个子元素换行挤压布局。
4. **el-tree getCheckedNodes 返回 tree data 包装对象**（{id, label, node, isLeaf}），不是结构节点——用 `d.node` 解包，否则属性面板拿不到格式。
5. **Promise.all 里混一个 404 端点会整体失败**：loadDocument 曾调不存在的 `GET /documents/{id}`。关键请求和非关键请求要拆开。

### P1 级（性能/体验）

6. **5000+ DOM 节点禁用 CSS transition**（hover/选中动画 = 鼠标卡顿）。
7. **el-tree 懒加载 + setCheckedKeys 批量**；setChecked 循环 ×5000 不可接受。
8. **大 zip 的媒体文件必须磁盘缓存 + immutable HTTP 缓存**，否则图片请求饿死 API 线程池。
9. **v-html 大预览建 DOM 索引 Map**；querySelector per-op 是主线程杀手。
10. **scrollIntoView smooth 在大文档改 instant**。
11. **TOC 域缓存条目必须跳过**（fldChar begin→end 状态机），否则双目录。
12. **Track Changes 必须递归提取 w:ins、跳过 w:del**，否则预览大面积空白。
13. **Wingdings bullet 是私有区字符**（U+F000-F0FF），浏览器显示豆腐块，必须映射（F06C→●、F06E→■、F075→○、F0A7→▪、F0B7→•）。
14. **多级编号续编三要素**：每级 lvlText 只引用到当前级 + level_num_fmts 分级格式 + isLgl 强制十进制上级。
15. **el-alert slot 内按钮 @click 不触发**：用 data-属性 + window click 委托。

### P2 级（环境/工具链）

16. **Vite build 在 safe-delete 沙箱下 emptyDir 失败**：第一次构建报 rmSync 错误，再跑一次即成功（dist 已空）。打包脚本里直接跑两次。
17. **Git Bash 下 taskkill 用 `//f //pid`**（或直接用 PowerShell Stop-Process）。
18. **curl -o 写文件用绝对路径**（相对路径在 Git Bash/Windows Python 混用时解析不一致）。
19. **datetime.utcnow() 已弃用**（61 个 warnings）：应改 `datetime.now(datetime.UTC)`，未改但无碍运行。
20. **cp 暂存源码文件在本环境不可靠**：验证备份对比后立即用 grep 确认源码状态（第七轮曾因此丢失暂存文件，幸未丢改动）。

---

## 5. 第八轮问题解决思路（本轮）

| 问题 | 根因 | 修复 |
|---|---|---|
| 浏览大文档后概览/文档管理加载失败 | media 端点每请求开 42MB zip，504 图占满线程池 | 磁盘缓存 + immutable + preview 预热 |
| 滚动到新区域卡顿 | 图片按需从 zip 读取 + 同步解码 | 同上 + decoding="async"（第七轮已去 transition） |
| 预览无段落编号 | 未模拟列表计数器 | structure_parser 计数器模拟 + 样式链 numPr 回溯 + Wingdings 映射 + 渲染前缀 |
| 编辑无进度反馈 | 大选择应用无提示 | 分块应用 + 状态栏进度条（applyProgress） |
| 状态/按钮无解释 | — | 状态中文映射 + el-tooltip/title 全覆盖 |
| 日志不好用 | 无搜索、筛选弱 | 默认全量 + 级别/操作/文档/关键词（后端 keyword LIKE） |
| 上传框小 | el-upload-dragger 默认 360×180 | CSS 100% 宽 × 160px 高 |
| 分页不可调 | 固定 20 | 20/50/100/200 + localStorage 记忆 |

**DocEditor v9.8 借鉴验证**：其不卡的原因是预览极简 DOM（截断 200 字符纯文本、无图片、无表格 HTML、无前端框架）。我们选择保留富预览但补齐缓存/解码/动画优化，实测效果达到同等流畅（FPS 62 满帧）。其编号文本提取（计数器模拟）思路直接移植到了 structure_parser。

---

## 6. AI 接手指引

### 环境
- **Python**：`py -3`（系统 Python 3.13，已装全部依赖 + pytest + httpx2）
- **Node**：`C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\node.exe`
- **前端构建**：`cd frontend && npm run build`（第一次可能因 safe-delete 拦截 emptyDir 失败，再跑一次）
- **后端测试**：`py -3 -m pytest backend/tests -q`（基线：41 passed + 1 failed=test_invalid_file_upload 原有隔离问题）
- **启动**：`py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- **基准文档**：`深信服超融合HCI6120技术白皮书.docx`，doc_id=`e6e9b493-e52e-4b55-8dd5-8b821c4008d3`（已入库）
- **CDP 测试脚本**：`C:\Users\Administrator\.workbuddy\binaries\node\workspace\`（perftest.js / perftest2.js / regresstest.js）

### 硬性规则（AI_Coding_Guidelines.md）
1. **修改任何已有文件前先备份**到 `.backup/YYYY-MM-DD_HHmmss/`（按原相对路径），输出 `✅ 已备份:` 确认行；备份目录超 20 个删最旧。
2. 不加新依赖；不改 start.bat/stop.bat/config.yaml 结构/PyInstaller 逻辑；不改 storage/original/。
3. schema 向后兼容（新字段必须 Optional 带默认值）。
4. 响应协议：L1 直接改 / L2 影响分析+改 / L3 影响分析+测试+改+列人工验证项。

### 常见任务入口
- 解析问题（预览内容缺失/结构错）→ `structure_parser.py` + `styles_parser.py`（样式链）
- 格式不生效 → `format_engine.py` 的 `_apply_action_to_element` + `rule_engine.match_rules`
- 编号问题 → `numbering_engine.py`（修改）+ `numbering_parser.py`（解析）+ structure_parser 的计数器模拟
- 预览性能 → Editor.vue 的 previewIndex/syncPreviewHighlight/schedulePreviewStyle 三件套
- API 慢/超时 → 检查是否有请求在占线程池（大 zip 操作要缓存）

### 遗留待办
- format_engine 只改第一个 run 的 rPr（多 run 段落不完整）
- 任务结果：`process_batch_task` 不写 `task.result_json`（TaskDetail 处理结果表空）+ 前端 batch-download 传 `{document_ids:[...]}` 对象但后端期望纯数组（会 422）——**下一优先级**
- PyInstaller 打包后 frontend_dist 路径（`__file__` 相对）在 _internal 下失效
- Diff 可视化视图（目前只 console.log）
- 结构树右键菜单 / 键盘导航 / 展开状态记忆
- 加密文档处理（msoffcrypto 未集成）
- datetime.utcnow() → datetime.now(UTC) 全局替换（61 处 warnings）
- 多选共同配置为 null 的字段会被 Object.assign 写回覆盖（多选编辑时注意）

---

## 7. 实测数据（第八轮，CDP headless Chrome）

| 场景 | 结果 |
|---|---|
| 编辑器加载（5574 预览节点） | 935ms |
| 快速滚动全文档 ×3 轮 | 每轮 ~820ms，**无 longtask** |
| 浏览后返回概览 | **511ms**（修复前十几秒超时） |
| 文档管理页 | **513ms**，20 行正常 |
| 编号标签渲染 | **1806 个**（1./2./3./●/■ 等） |
| media 请求（缓存后） | **10ms**，带 immutable 头 |

第七轮（性能优化）对比：全选 432ms→42ms；全选态改属性 649ms→342ms；点击 2.2ms→0.3ms。

---

*本文档随 v4 交付。后续迭代请追加到 .workbuddy/memory/ 日志并同步更新本文档。*
