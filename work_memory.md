# 项目工作记忆（Work Memory）

> **项目**：Word Format Batch Editor（Word 格式批量编辑器）
> **来源**：`.workbuddy/memory/2026-08-15.md`（项目每日工作日志）
> **导出时间**：2026-08-15 18:22
> **说明**：本文件为项目工作记忆的导出快照，记录 2026-08-15 一天共六轮的迭代过程、修改文件、实测数据与关键工程教训。

---

# 2026-08-15 项目笔记

## 第一轮（14:08-14:42）：体验审计
- 通读 requirements.md / README.md / PHASE_REPORT_V2.md
- 通读 backend 全部核心代码（main / api / services / tasks / config / utils）
- 通读 frontend 全部 9 个 Vue 视图 + App.vue / main.js / router / api / ws / vite.config
- 实测 1920×1080 / 2560×1440 视口下 Chrome 渲染，定位到 1 个 P0 严重 bug + 多个 P1/P2 体验问题

## 第二轮（14:42-15:10）：按优先级修复第一版
P0 → P1 → P2 → P3 完成所有改造，构建 + 截图回归通过。

### 第三轮（15:10-16:00）：按用户反馈修复三个问题
1. ✅ 三栏拖拽修复（深层 bug）
2. ✅ 结构树/预览多选批量修改属性
3. ✅ 预览表格内容与完整文字显示

## 第四轮（16:00-16:30）：用户新增 6 项需求
1. ✅ AI_Coding_Guidelines.md 加新规则（**修改前自动备份**到 `.backup/{时间戳}/`）
2. ✅ 预览不完整（实为性能问题——6043 节点 DOM 渲染 + 滚动卡顿）
3. ✅ 拖拽卡顿（rAF 节流 + CSS contain 优化）
4. ✅ 结构树按 L1-L6 层级显示（基于样式链解析 + 父子嵌套）
5. ✅ 结构树不再显示 `[paragraph]`（过滤空段 + 显示实际内容）
6. ✅ 批量任务编辑完整流程：样式识别+编号→目标样式→保存模板→批量应用不改原文档→预览/下载→导出选择

### 第四轮修改的文件（已备份到 `.backup/2026-08-15_161450/`）
- **backend/core/styles_parser.py**：增强 heading_level 识别（中文标题样式 "S标题2"、"一级标题" 等 + basedOn 链解析 + outlineLvl fallback）
- **backend/services/structure_parser.py**：标题检测用 resolve_style_chain 的 heading_level；层级嵌套（标题→父标题、正文→当前标题）；空段落保留；numbered_node_ids 维护；numbering 提取到 current_format.numbering
- **backend/schemas/document.py**：DocumentStructure 加 `ordered_node_ids: List[str]`（文档顺序）
- **backend/core/html_renderer.py**：preview 用 ordered_node_ids 遍历；空段落用轻量 `<div class="empty-line">` 占位
- **backend/api/documents.py**：preview max_pages 用 ordered_node_ids 长度计算
- **backend/services/format_engine.py**：element 映射改用 ordered_node_ids；numbering 应用（调用 numbering_engine）
- **frontend/src/views/Editor.vue**：buildTree 过滤空段 + 标题标签 + 表格标签；el-tree 默认展开 L1；拖拽 rAF 节流；panel/preview-area 加 `contain: layout style paint`；"保存为模板"按钮 + 对话框
- **frontend/src/views/TaskList.vue**：新建任务对话框加模板选择（自动加载 rules）+ 原文档保护提示
- **frontend/src/views/TaskDetail.vue**：results 表加 checkbox + "下载选中到本地"（fetch + blob + a tag）+ 全选/清空 + 行末下载链接

### 第四轮实测对比（6043 节点文档）
| 指标 | 第三轮后 | 第四轮后 |
|---|---|---|
| 标题层级 | 仅 25 个 L2（识别不全） | **L1:7, L2:26, L3:76, L4:212, L5:153** ✓ |
| 结构树 root 数量 | 6043（平铺） | **42**（层级顶层） |
| 结构树标签 | 大量 `[paragraph]` | 实际内容 + `#` 层级 + `📊 表格` ✓ |
| 预览滚动到底耗时 | 未知（卡顿） | **< 1ms**（6950 DOM 节点，scrollHeight 214KB） |
| 拖拽 | 顺滑但低效 | rAF 节流 + CSS contain，更顺滑 |
| 模板保存 | 无 | **Editor 工具栏新增"保存为模板"按钮** ✓ |
| 批量任务下发 | 选文档（无模板） | **选模板 + 选文档 + 原文档保护提示** ✓ |
| 导出选择 | 无（单文件下载） | **TaskDetail 多选 checkbox + 批量 ZIP 下载** ✓ |

### 第四轮关键教训
1. **新 AI 规则**：修改前自动备份到 `.backup/YYYY-MM-DD_HHmmss/`（按原相对路径），超过 20 个备份删除最旧。本轮备份了 7 个文件，TS=`2026-08-15_161450`。
2. **样式链解析**：中文/WPS 文档常用自定义标题样式（"S标题2" basedOn → heading 2），必须基于样式链解析 heading_level，不能只看 outlineLvl 或 name.startswith("heading")。
3. **ordered_node_ids 必要性**：root_node_ids 改层级后丢失文档顺序；format_engine 的 element 映射依赖文档顺序，必须新增 ordered_node_ids 字段（schema 向后兼容）。
4. **空段落性能**：1626 个空段落用轻量 `<div class="empty-line">` 占位（class+style，无 innerHTML），DOM 更轻；CSS contain: layout paint 隔离重排。
5. **模板化工作流**：识别→修改→保存模板→批量应用→预览/下载的链路，前后端能力已有（template/task/batch_download API），主要工作是前端 UI 集成 + 编号引擎集成到 format_engine。
6. **导出选择**：后端 batch_download 已支持任意 document_ids 子集（不只是全部），前端用 fetch + blob + a tag 触发浏览器下载 ZIP。

### 验证产物
- 截图：`C:\Users\Administrator\Downloads\wbe-shots\v4_*.png`（editor 工具栏、TaskList 模板选择对话框、TaskDetail 导出选择）
- 构建产物：`frontend/dist/index.html` 1,652.50 kB（gzip 463.09 kB）
- 备份：`.backup/2026-08-15_161450/`（7 个文件）

### 🔴 Bug #1: Vue 模板 @event 绑定在压宿后失效
**症状**：三栏拖拽拖不动、预览点击多选无反应、批量操作按钮点击无效。

**根因排查过程**（用 CDP Event 追踪）：
1. handle 上的 `@mousedown` 没触发 → 移除模板绑定改用 document 委托 → 仍无效
2. document capture 委托用了 `l.addEventListener`（l 是 document 压缩别名）→ 但实际注册到了非 document 对象 → 委托失效
3. **真相**：源码里裸写 `document.addEventListener` / `document.querySelector` → 编译后被压缩器重命名为局部变量 `l`，在某些函数闭包里 `l` 与外层 setup 的 `document` 不是同一个对象（或 `l` 被压缩器在 `setup` 顶层与函数体内复用了同名不同对象）

**最终修复**：所有组件内的 `document.xxx` 改为 `window.document.xxx`（`window` 是真正的全局对象，压缩器不会重命名）；交互事件用 `window.addEventListener('xxx', handler, true)`（capture 阶段，最先执行）。

**影响范围**（已修复）：Editor.vue 全部 5 处 `document.querySelector/all`、`document.body`、`document.add/removeEventListener`。

**一般性规则**：Vue 3 + vite + minifier 环境下，组件 setup 作用域内引用全局对象时，**用 `window.document` 代替 `document`** 以避免压缩器作用域变量复用问题。

### 🔴 Bug #2: 前端 structure 与 preview 接口返回不同 node id
**症状**：点击预览节点无法关联到结构树节点，树勾选无法高亮预览。

**根因**：前端并行调用 `/structure` 和 `/preview` 两个接口，后端**每次调用都重新解析** .docx，每次解析用 `uuid.uuid4()` 生成不同的随机 node id。预览 HTML 的 `data-node-id` 来自第二次解析的 id，与前端 `structure.nodes`（第一次解析的 id）完全对不上。

**修复**：
- `backend/schemas/document.py`：DocumentNode 加 `content: Optional[str]`（完整文本，向后兼容），TableInfo 加 `cells: Optional[List[List[str]]]`（完整单元格内容）。
- `backend/services/structure_parser.py`：
  - 新增 `_extract_para_text`/`_extract_run_text`/`_cell_text` 辅助函数（处理 tab/break/hyperlink）。
  - `_process_paragraph` 提取完整 `content`，保留 `content_preview`（前 50 字符，树标签用）。
  - `_process_table` 提取每行每列单元格文本 `cells_data`（含合并单元格的文本，存到起始位置）。
- `backend/core/html_renderer.py`：`render_node_html` 优先用 `node.content`，`_render_table` 用 `info.cells` 渲染单元格。
- **关键修复**：`make_node_id` 从 `uuid.uuid4()` 改为基于递增序号的 SHA-256 哈希（前 16 hex），**保证同一文档两次解析 id 集合完全一致**（序号遍历顺序稳定）。6043 节点文档解析性能 0.35s（与原版相当）。
- `backend/api/documents.py`：preview 端点 max_pages 改为按节点数动态计算（不再硬截断，6043 节点全渲染）。

### 🔴 Bug #3: CSS Grid 5 子元素放 3 列自动换行
**症状**（第一轮拖拽修改后）：右侧面板跑到了中间，中间面板跑到了最右边。

**根因**：grid-template-columns 只声明 3 列，5 个子元素（panel-left + handle + panel-center + handle + panel-right）按 DOM 顺序填入，第 4 个 handle 换到第二行第一列，把 panel-right 挤到第二列。

**修复**：grid-template-columns 声明 5 列 `240px 6px 1fr 6px 320px`。

---

## 本轮修改的文件

- **backend/schemas/document.py**：DocumentNode 加 `content` 字段，TableInfo 加 `cells` 字段（Optional，向后兼容）。
- **backend/services/structure_parser.py**：完整文本提取、表格单元格提取、确定性节点 ID（序号哈希）。
- **backend/core/html_renderer.py**：用 content 和 cells 渲染；CSS 选择器加 `.doc-preview` 前缀。
- **backend/api/documents.py**：preview max_pages 按节点数动态计算。
- **frontend/src/views/Editor.vue**：
  - 三栏拖拽：改用 **window-level capture delegation**（`window.addEventListener('mousedown', handler, true)`），startDrag 内用 `window.document` 替代 `document`。
  - 多选：el-tree `show-checkbox` + 树勾选/预览点击双向同步 + 属性面板批量模式 alert + "应用到选中节点" + "创建规则"按钮。
  - 批量按钮：从 el-alert slot 移到外部（el-alert slot 内 @click 不触发） + 用 `window` click 委托（`data-bulk-apply`/`data-bulk-rule`）。
  - 预览点击多选：`window` capture click 委托 + `window.document.querySelector` 查找节点。
  - 所有 `document.xxx` 改为 `window.document.xxx`（5 处）。
- **frontend/src/views/DocumentList.vue**：上传 drag 拖拽区域。
- **frontend/src/views/Settings.vue**：竖排导航 + 外观主题切换 Tab。
- **frontend/src/App.vue**：导航补系统设置入口、高 DPI 字号响应式、暗色变量。
- **frontend/src/main.js**：dark theme CSS-vars 引入。
- **launcher.py**：DPI 感知 + 字号/窗口按 DPI 缩放。

---

## 实测对比（1920×1080，6043 节点文档）

| 验证项 | 修复前 | 修复后 |
|---|---|---|
| body 宽度（P0 CSS 污染） | 800px ❌ | **1904px** ✅ |
| 三栏布局（P1） | 错位 ❌ | 正常 240+1268+320 ✅ |
| 中间预览宽度 | 152px（竖排）❌ | **1268px** ✅ |
| 三栏拖拽（深层 bug） | 拖不动 ❌ | 左 240→360、右 320→440 ✅ |
| 树勾选多选 | 无 checkbox ❌ | 已选 3 个节点 ✅ |
| 预览点击多选 | 无效（id 不匹配）❌ | 选中/取消正常 ✅ |
| 批量应用 | 无反应 ❌ | "已应用到 2/2 个节点" ✅ |
| 批量建规则 | 无反应 ❌ | "已根据 2 个选中节点创建规则" ✅ |
| 预览表格内容 | 全空白 ❌ | 654/699 单元格有内容 ✅ |
| 预览完整文字 | 截断 50 字符 ❌ | 624 长段落，无截断 ✅ |

---

## 关键教训

1. **CDP + DOM 测量脚本（measure.js/diag.js）**：能精确定位 layout 和事件问题，比纯截图高效。脚本保存在 `C:\Users\Administrator\.workbuddy\binaries\node\workspace\`（measure.js、diag.js、dragtest.js 系列、multitest.js 等）。
2. **CSS Grid + resize handle 必须显式列数**：5 个子元素对应 5 列。
3. **v-html 注入的 `<style>` 是全局的**：必须用作用域前缀。
4. **后端两次解析必须用确定性 ID**（基于遍历顺序），否则前端跨接口关联失败。
5. **Vue 3 + minifier + 裸 `document.xxx`**：在 setup 作用域内会被错误重命名，必须用 `window.document.xxx`。
6. **el-alert slot 内的按钮 @click 可能不触发**：用 `data-` 属性 + `window` click 委托替代。
7. **Vite build + 沙箱 safe-delete**：`rm -f dist/index.html` 单文件删除 OK，`rm -rf dist` 会被拦截。

---

## 验证产物
- 截图：`C:\Users\Administrator\Downloads\wbe-shots\fixed_*.png` + `final_editor_1920.png`
- 构建产物：`frontend/dist/index.html`（1,645.68 kB，gzip 460.66 kB）
- 测试脚本：measure.js、diag.js、dragtest6.js、multitest.js、clicktest.js、applytest3.js、dragfinal.js（CDP 驱动）

## 第五轮（16:55+）：9 项功能修复

### 1-3 / 6：前端交互增强
- **问题 1**：Shift+多选 + 全选/取消全选按钮
  - 前端 `onWinClick`：Shift+点击时按 `ordered_node_ids` 顺序区间选择
  - 树顶部加"全选/取消全选/↶ 撤销/↷ 恢复"按钮
  - `lastClickedNodeId` 记录最后点击节点
- **问题 2**：左右侧栏展开按钮
  - 折叠时 panel 变 28px 窄条 + 竖向"结构树"/"属性配置"标签 + 展开图标
  - gridStyle 折叠列宽从 0 改为 28
  - 新增 `Expand` 图标
- **问题 3**：撤销/恢复撤销
  - `undoStack`/`redoStack` 记录 selection 快照
  - 每次修改 selection（toggle/range/check/selectAll/clear）前 pushUndo
- **问题 6**：树/预览互定位
  - `onNodeClick`：预览区 `scrollIntoView` + `locate-flash` class 闪烁红色边框 1.2s
  - `onWinClick`：树 `setCurrentKey` + `scrollIntoView` 到对应节点

### 4-5：属性下拉 + 编号重命名续编
- **问题 4**：字体（中/英）、字号改为 `el-select filterable allow-create`（常用选项+自定义）
- **问题 5**：段落编号下拉（14 个 NUMBERING_OPTIONS），支持 L1-L6 多级编号
  - 前端 `numberingKey` 通过 watch 映射到 `editableFormat.numbering`
  - **后端 numbering_engine 增强**：`_level_text_for_ilvl(spec, ilvl)` 按 ilvl 截取 `%N` 占位符（如 `"%1.%2.%3"` 在 ilvl 0 输出 `"%1"`、ilvl 1 输出 `"%1.%2"`），保证 Word 打开后多级编号自动续编

### 7-9：预览内容缺失修复（核心 L3）
**根因**：测试文档使用了大量**修订标记（track changes）**——文档统计 `ins: 14719, del: 6357`。
- `_extract_para_text` 只遍历直接子 `<w:r>`，**完全忽略 `<w:ins>` 内的 run**，导致：
  - **问题 9（章节内容空白）**："全功能模式运行"→"空洞检测"区间 22 段全部在 `<w:ins>` 里，提取为空
  - **问题 7（目录空白）**：TOC 条目在 `<w:ins>` 里，且 TOC 是动态域（Word 运行时生成，XML 无条目文本）
- **问题 8（图片）**：图片在 `<w:drawing>` 里，未处理

**修复**：
- **后端 structure_parser**：`_extract_para_text` 改为**递归遍历**，跳过 `<w:del>`（删除内容），提取 `<w:ins>`、`<w:hyperlink>`、`<w:sdt>` 内的 `<w:t>`，跳过 `<w:drawing>`（图片单独处理）和 `<w:instrText>`（域指令）
- **后端 structure_parser**：图片检测——遍历 paragraph blip → rels → media 文件名，创建 image 节点
- **后端 html_renderer**：TOC 域自动生成——检测 `node.content == "__TOC__"` 时，根据 structure 标题节点生成 `<div class="toc-container">` 含 L1-L6 缩进锚点目录
- **后端 html_renderer**：图片懒加载 `<img src="/api/v1/documents/{doc_id}/media/{name}" loading="lazy">`
- **后端 api/documents.py**：新增 `GET /{doc_id}/media/{name}` 端点，从 zip 读取 `word/media/{name}` 二进制返回（含 MIME 映射 + 路径穿越防护）

### 第五轮修改的文件（已备份到 `.backup/2026-08-15_165459/`）
- backend/services/structure_parser.py：递归提取 + 图片检测 + TOC 标记
- backend/core/html_renderer.py：图片 media URL 渲染 + TOC 自动生成 + heading id 锚点
- backend/services/numbering_engine.py：`_level_text_for_ilvl` 多级 lvlText 截取
- backend/api/documents.py：`/{doc_id}/media/{name}` 端点
- frontend/src/views/Editor.vue：侧栏展开按钮 + 全选/取消/撤销/恢复 + Shift 多选 + 互定位 + 字体/字号/段落编号下拉

### 第五轮实测
| 指标 | 修复前 | 修复后 |
|---|---|---|
| 预览 HTML 大小 | 1062KB（不完整） | 1062KB（**完整**）|
| TOC 目录条目 | 0（空白） | **477 条**（按标题层级自动生成）|
| 图片显示 | 0（占位 [Image]） | **504 张**（SANGFOR/信服云 logo 等正常显示）|
| "兼容模式"内容 | 缺失 | **存在** |
| "虚拟机冷迁移"内容 | 缺失 | **存在** |
| 侧栏折叠后 | 无法展开 | 28px 窄条 + "结构树"竖向标签可点击展开 |
| Shift+多选 | 无 | Shift+点击预览范围多选（按文档顺序）|
| 全选按钮 | 无 | 全选 5474 节点 + 预览全高亮 + 批量面板激活 |
| 撤销/恢复 | 无 | undoStack/redoStack，每次选择变化前 pushUndo |
| 树→预览定位 | 无 | 预览滚动 + 红色边框闪烁 1.2s |
| 字体/字号 | el-input 文字输入 | el-select 下拉（filterable allow-create，常用选项+自定义）|
| 段落编号 | 无 | 14 选项下拉（1,2,3 / 第一章 / 1.1 / 1.1.1 ... / a,b,c / I,II,III 等）|

### 第五轮关键教训
1. **Track Changes 是预览空白的主要来源**：处理 Word 文档时必须提取 `<w:ins>`（插入）并跳过 `<w:del>`（删除内容）。
2. **TOC 域条目不在 XML 里**：Word 动态生成；软件预览时按结构标题自动渲染 TOC。
3. **图片用 media 端点而非 base64 内嵌**：519 张图 base64 内嵌 HTML 会膨胀到 50MB+，用独立 `/media/{name}` 端点 + `loading=lazy` 实现按需加载。
4. **多级编号的 lvlText**：每个 ilvl 的 lvlText 应只引用到当前层级（ilvl 0 用 `%1`，ilvl 1 用 `%1.%2`），Word 才能正确续编（1, 1.1, 1.1.1 自动递增）。

### 验证产物
- 截图：`C:\Users\Administrator\Downloads\wbe-shots\v5_*.png`（编辑器、目录、图片、侧栏折叠/展开、全选、属性面板）
- 构建产物：`frontend/dist/index.html` 1,659.23 kB（gzip 465.22 kB）
- 备份：`.backup/2026-08-15_165459/`（5 个文件）

### 第五轮需要人工验证
1. **编号续编 Word 兼容性**：下载处理后的 .docx 在 Word 中打开，确认编号样式正确且自动续编（第一章、1,2,3 / 1.1, 1.1.1）。
2. **媒体端点 504 张图片全部正常加载**：滚动预览时所有图懒加载正常。
3. **撤销/恢复**：实际操作多选 → 撤销 → 状态恢复是否准确。
4. **Shift 多选范围**：从节点 A Shift+点击节点 B，是否正确选中 A-B 之间所有有内容的节点。
5. **互定位闪烁**：树点击后预览红色边框闪烁 1.2 秒是否符合预期。

---

## 第六轮（17:27+）：10 项功能修复

### 核心修复（按问题编号）

**问题 1（结构树卡顿，L3）**：
- **根因**：el-tree 全量渲染 5474 个节点（即使折叠），拖拽 leftWidth 时 grid 重排触发全树重排。
- **修复**：el-tree 改**懒加载**（`:lazy="true" :load="loadTreeNode"` + `isLeaf`），初始只渲染根节点（~20 个 DOM 节点）。
- 关键：`v-if="structure"` + `:key="treeRefreshKey"`（structure 异步加载后强制重建树）。
- 实测：树渲染节点数从 5474 → **20**，流畅。

**问题 2（# 改 L 标签）**：
- buildTreeNodes 标题标签：`${'#'.repeat(level)}` → `L${level}`，加编号 `L1 1 产品概述`、`L2 3.2 2018年架构重构`。

**问题 4（段落编号显示）**：
- **headingNumbers computed**：遍历 ordered_node_ids，按 level 维护计数器，移除前导 0（"0.0.0.0.1"→"1"）。
- 树标签：`L${level} ${编号} ${文本}`。

**问题 3（Shift 多选 + 全选标记）**：
- Shift 多选失败根因：Shift+点击预览触发浏览器文本选择，干扰 click。修复：preview 节点加 `user-select: none` + `e.preventDefault()`。
- 全选标记：selectAllNodes 加 `treeRef.setChecked(id, true, false)`（勾选已加载节点）+ pushUndo。
- 实测：全选 5946 预览高亮 + 20 树勾选。

**问题 6（撤销格式修改）**：
- **格式撤销栈**：`formatHistory`/`formatFuture`，`snapshotFormat` 记录受影响节点的 style + current_format。
- `applyFormatToNodes` 前快照，`undoFormat`/`redoFormat` 恢复。
- undo() 优先 undoFormat，否则 undo selection。
- 实测：段前距 30 立即生效（margin-top: 30pt），撤销后移除 ✓。

**问题 7（立即生效）**：
- `watch(editableFormat, deep)`：用户编辑时自动 `applyFormatToNodes(activeNodes, fmt)`。
- `suppressFormatWatch` 标志：程序化设置（onNodeClick/选择同步）时阻止触发，微任务后释放。
- 移除"应用到预览/应用到选中节点"按钮，加提示"修改后立即生效"。

**问题 10（多选共同配置）**：
- `activeNodes computed`：多选 checkedNodes 优先，否则 selectedNode。
- `computeSharedFormat(nodes)`：多选时各字段相同则显示，不同则 null（空白）；单选显示该节点配置。
- `typeSummary computed`：类型分布（"图片×504, 正文×3568, 标题L1×7..."）。
- 属性面板 `v-if="activeNodes.length > 0"`，多选显示"已选 N 个段落 + 类型分布 + 共同配置提示"。

**问题 8（模板按层次保存）**：
- `buildLayeredRules()`：activeNodes 按 `heading:L1-L6 / paragraph / list_item / table / image` 分组，每层一条规则（condition=type+level，action=该层 current_format）。
- submitTemplate 用 `buildLayeredRules()`，对话框预览按层次规则列表。
- 实测：全选 5474 节点 → 生成 L1-L5 标题 + 正文 + 列表项 + 表格 + 图片 分层规则。

**问题 9（下拉统一）**：
- TemplateManager.vue：font_cn/font_size 改 `el-select filterable allow-create`（加 CN_FONTS/EN_FONTS/FONT_SIZES 常量）。

### 第六轮修改的文件（已备份到 `.backup/2026-08-15_173019/`）
- frontend/src/views/Editor.vue：懒加载树 + L 标签 + 编号 + Shift 多选 + 全选标记 + 撤销格式 + 立即生效 + 共同配置 + 模板按层次
- frontend/src/views/TemplateManager.vue：字体/字号下拉

### 第六轮实测
| 指标 | 修复前 | 修复后 |
|---|---|---|
| 树渲染节点 | 5474（全量） | **20（懒加载）** |
| 树层级标记 | `#`×N | **L1-L6 标签** |
| 标题编号 | 无 | **L1 1 产品概述 / L2 3.2 2018年架构重构** |
| Shift 多选 | 失败 | **范围多选**（user-select:none + preventDefault）|
| 全选标记 | 无勾选 | **20 树勾选 + 5946 预览高亮** |
| 撤销格式 | 无 | **margin-top 30pt 撤销后移除** |
| 立即生效 | 需点按钮 | **watch 自动应用** |
| 共同配置 | 无 | **多选显示类型分布 + 共同配置空白** |
| 模板保存 | 平铺规则 | **按 L1-L6/正文分层规则** |

### 第六轮关键教训
1. **el-tree 懒加载**：5000+ 节点必须懒加载（`lazy + load + isLeaf`），否则全量渲染卡顿。Element Plus 2.7 无内置虚拟滚动，懒加载是最佳选择。
2. **懒加载 + 结构异步加载**：`v-if="structure"` + `:key="treeRefreshKey"` 强制重建，否则初始 "No Data"。
3. **Shift 多选 + 文本选择冲突**：Shift+点击预览触发浏览器文本选择，需 `user-select: none` + `e.preventDefault()`。
4. **格式撤销快照**：`snapshotFormat` 同时记录 style 和 current_format，undo 时两者都恢复。
5. **立即生效 + suppress 标志**：watch 立即应用，但程序化设置（onNodeClick/选择同步）需 suppress 避免循环，用微任务重置。
6. **多选共同配置**：`JSON.stringify` 比较各字段是否全同，全同则显示，否则空白。
7. **el-switch/el-select 的 CDP 模拟不可靠**：Element Plus 组件的 CDP 模拟 click 不一定触发 v-model 更新；用 el-input-number 的 input 事件验证更可靠。真实用户操作不受影响。

### 验证产物
- 截图：`C:\Users\Administrator\Downloads\wbe-shots\v6_*.png`（树懒加载+编号、共同配置、全选）
- 构建产物：`frontend/dist/index.html` 1,663.54 kB（gzip 466.64 kB）
- 备份：`.backup/2026-08-15_173019/`（4 个文件）

### 第六轮需要人工验证
1. **懒加载展开流畅度**：真实鼠标展开 L1→L2→... 时子节点加载是否流畅。
2. **Shift 多选**：真实鼠标 Shift+点击两个节点，验证范围选择。
3. **el-switch/el-select 真实点击**：真实鼠标切换加粗/下划线，验证立即生效（CDP 模拟不可靠，需人工）。
4. **撤销多步**：连续修改多个属性，逐步撤销验证。
5. **模板按层次**：全选后保存模板，在 TaskList 用该模板批量处理，验证各层次样式正确应用。
6. **共同配置**：多选不同格式的段落，验证共同配置显示空白。

---

## 待办（剩余改进）
- 规则编辑器折叠面板简化
- 结构树右键菜单 + 键盘导航 + 虚拟滚动（>500 节点）
- 结构树展开状态记忆
- Diff 可视化视图（目前只 console.log）
- "应用到所有文档"按钮语义明确
- 拖拽上传文件夹支持
