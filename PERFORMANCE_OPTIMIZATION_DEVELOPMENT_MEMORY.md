# 大型文档编辑器性能优化开发记忆

> 用途：沉淀大型 DOCX/HTML 文档在 Web 编辑器中的解析、预览、结构树和批量交互优化经验，可迁移到其他项目。

## 一、问题特征

典型场景：

- 单个 DOCX 解析后包含数千个段落、标题、表格和图片。
- 预览区通过 `v-html` 或类似方式渲染 HTML。
- 左侧结构树需要展开、折叠、搜索和多选。
- 右侧属性面板要根据选中节点实时同步。
- 用户打开文档时可能同时触发解析、HTML 渲染、图片提取和前端 DOM 挂载。

常见表现：

- 首次打开文档长时间无响应。
- 浏览器一次性创建大量 DOM 节点，滚动和点击掉帧。
- 全部展开结构树时页面冻结。
- 勾选一个节点却触发整个节点集合重新计算。
- 修改格式时全量更新预览样式。
- 后端缓存命中后仍然卡顿，因为瓶颈已经转移到了浏览器 DOM 和 Vue 响应式更新。

## 二、总原则

### 1. 把重工作移出用户点击路径

不要在用户点击“打开文档”的同一个请求里完成所有工作。采用：

```text
文档列表加载
  -> 后台低并发预解析
  -> 持久化结构和预览缓存
  -> 用户打开时优先读取缓存
```

### 2. 区分三个性能层次

```text
解析层：DOCX XML 解析、样式解析、图片提取
服务层：缓存、接口响应、分片传输
浏览器层：Vue 响应式、DOM 数量、布局和绘制
```

只优化其中一层通常不够。后端解析变快后，如果仍然一次性挂载 5,000 个节点，浏览器依然会卡。

### 3. 数据缓存和交互状态分离

- 文档解析结果：持久化缓存。
- 当前勾选状态：前端内存中的轻量索引。
- 展开/折叠状态：组件内部状态或本地布局状态。
- 不要把完整结构对象和频繁变化的选择状态全部放进深度响应式对象。

## 三、后端预解析与持久化缓存

### 1. 后台低并发预解析

推荐使用单线程或很小的线程池：

```python
_executor = ThreadPoolExecutor(max_workers=1)
```

原因：大型 DOCX 解析同时消耗 CPU、内存和磁盘 I/O。并发过高可能使所有请求都变慢。

网页进入后，将未完成的文档加入队列；不要在 Web 请求线程中同步处理完整文档。

### 2. 缓存版本必须可失效

缓存不能只用 `document_id` 命名。至少组合以下信息：

```text
document_id
源文件 mtime 或 sha256
parser_version
renderer_version
```

推荐路径：

```text
storage/temp/preview_cache/{document_id}/structure-{source_version}.json
storage/temp/media_cache/{document_id}/image1.png
```

缓存命中条件：

```python
parse_status == "READY"
source_version == current_source_version
cache_version == current_cache_version
cache_file.exists()
```

### 3. 状态字段单独设计

文档处理状态和预览解析状态不是同一件事。建议单独维护：

```text
NOT_STARTED  未开始
QUEUED       排队中
PARSING      解析中
READY        已缓存
STALE        源文件变化，缓存过期
ERROR        解析失败
```

最小字段：

```text
parse_status
parse_error
parse_started_at
parse_completed_at
parse_source_version
parse_version
```

### 4. 状态接口

推荐提供：

```text
GET  /documents/{id}/parse-status
POST /documents/{id}/parse
POST /documents/preparse
```

文档列表返回 `parse_status`，前端可以直接展示，不必为每一行额外发请求。

### 5. 图片提前提取

DOCX 是 ZIP 容器。若每次图片请求都重新打开 ZIP，会在滚动时产生大量 I/O。

后台预解析阶段可将 `word/media/*` 提取到本地媒体缓存，并给图片接口返回长期缓存头：

```http
Cache-Control: public, max-age=31536000, immutable
```

注意：文件名必须做路径安全处理，只允许使用 basename，避免路径穿越。

## 四、预览区优化

### 1. 不要一次性挂载完整 HTML

最重要的优化是分段加载：

```text
首屏加载前 100~200 个节点
滚动接近底部时再请求下一段
每次追加固定数量节点
```

后端接口可支持：

```text
GET /documents/{id}/preview?offset=0&limit=120
```

前端只把已加载分段放入页面。

### 2. 分段返回要避免重复外层结构

首段可以包含：

- 根容器
- 样式块
- 首批节点

后续段只返回节点 HTML，不要重复插入完整 `<style>` 或外层容器。

### 3. HTML 分段解析注意事项

不要简单依赖字符串切片破坏未闭合标签。更稳妥的方式：

- 后端按节点边界生成完整片段。
- 每个分段内部保证标签闭合。
- 前端以分段容器分别挂载。
- 节点 ID 必须全局稳定且唯一。

### 4. 预览节点索引

不要每次点击都对 5,000 个节点执行 `querySelector`。在每次分段挂载完成后建立：

```javascript
previewIndex = new Map()
for (const el of root.querySelectorAll('[data-node-id]')) {
  previewIndex.set(el.dataset.nodeId, el)
}
```

之后定位节点使用：

```javascript
previewIndex.get(nodeId)
```

### 5. 增量高亮

维护上一次高亮集合：

```javascript
let lastHighlighted = new Set()
```

本次选择变化时：

1. 只移除已经取消的 ID。
2. 只添加新选中的 ID。
3. 不要每次重新遍历整个预览 DOM。

## 五、结构树优化

### 1. 使用懒加载和只构造可见子节点

Element Plus `el-tree` 等组件不要一次传入全部树节点。使用 lazy load：

```text
根节点展开时构造根子节点
标题展开时再构造其 children_ids
```

空段落和没有导航价值的空列表项可以过滤掉。

### 2. 结构数据使用浅引用或非响应式对象

Vue 3 中，大型结构对象不应该被深度代理：

```javascript
const structure = shallowRef(null)
structure.value = markRaw(serverData)
```

避免 5,000 个节点和每个节点的格式对象都进入深度响应式系统。

### 3. 勾选状态使用 Set 保存 ID

不推荐：

```javascript
const checkedNodes = ref([])
checkedNodes.value.push(node)
```

推荐：

```javascript
const checkedIdSet = new Set()

checkedIdSet.add(nodeId)
checkedIdSet.delete(nodeId)

const checkedNodes = shallowRef([])
checkedNodes.value = Array.from(
  checkedIdSet,
  id => structure.value.nodes[id]
).filter(Boolean)
```

优点：

- 查找和去重接近 O(1)。
- 不因单个勾选让深层数组发生大量响应式变更。
- 只有属性面板需要时才生成节点数组。

### 4. 批量勾选只调用一次组件 API

不要循环调用：

```javascript
for (const id of ids) tree.setChecked(id, true)
```

应该：

```javascript
tree.setCheckedKeys(ids, false)
```

并且在批量调用后再同步一次预览和属性面板。

### 5. 勾选同步延迟到下一帧

结构树组件触发勾选事件后，使用 `requestAnimationFrame` 合并短时间内的多次更新：

```javascript
let pendingJob = 0

function scheduleSelectionSync() {
  const job = ++pendingJob
  requestAnimationFrame(() => {
    if (job !== pendingJob) return
    syncPreviewHighlight()
    syncEditableFromSelection()
  })
}
```

如果用户连续点击多个节点，过期任务会被丢弃。

### 6. 全部展开/折叠分帧执行

一次性展开几百个标题会触发大量组件计算和布局。改为每帧处理固定数量：

```javascript
function runTreeBatch(ids, action) {
  let index = 0
  function step() {
    const end = Math.min(index + 20, ids.length)
    for (; index < end; index += 1) {
      action(ids[index])
    }
    if (index < ids.length) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
```

批量大小可以按设备调整，常见范围为 16~32。

### 7. 必要时使用虚拟树

分帧只能避免页面长时间冻结，不能减少最终 DOM 数量。

如果“全部展开”后仍有数千个树节点同时存在，应进一步使用：

- 虚拟树
- 虚拟列表
- 只渲染可视区域节点

这是结构树性能的最终方案。

## 六、本地缓存的正确边界

### 推荐分层

```text
后端本地磁盘：持久化解析结构、HTML 分段、图片
前端内存：当前文档结构索引、勾选 Set、预览 DOM 索引
浏览器 HTTP 缓存：图片和稳定的预览分段
IndexedDB：可选，用于离线或跨页面复用，不作为唯一数据源
```

### 不建议把完整解析结果只放 IndexedDB

原因：

- 浏览器缓存可能被清理。
- 敏感文档内容长期留在浏览器目录。
- 版本失效和同步逻辑更复杂。
- IndexedDB 不能解决大量 DOM 挂载带来的卡顿。

本地 Windows 软件中，如果后端也是本机进程，后端磁盘缓存本身就是“用户本地缓存”，通常比浏览器数据库更可控。

## 七、格式修改的性能策略

### 1. 样式更新分块

对大量选中节点应用样式时，不要一次性写完所有 DOM：

```text
每帧处理 300~600 个节点
显示处理进度
允许新操作覆盖旧任务
```

### 2. 保存原始状态用于撤销

撤销快照只保存必要字段：

```text
node_id
旧 style
旧 current_format
```

不要复制整份结构树。

### 3. 防抖属性编辑

输入字号、字体或颜色时，使用短防抖，避免每个字符都触发全量处理：

```javascript
setTimeout(applyFormat, 80~150)
```

## 八、常见失败方案

### 失败方案 1：只做后端缓存

后端接口变快，但前端仍一次性挂载全部节点，浏览器继续卡顿。

### 失败方案 2：全部数据放 Vue `ref`

深度响应式代理大型对象，会让勾选和格式修改变慢。

### 失败方案 3：每个节点逐个调用组件更新

会造成大量组件事件、布局和重绘。

### 失败方案 4：把所有任务放在服务启动阶段

启动时同步解析全部文档，会导致服务看似“无法启动”。应该放入后台队列。

### 失败方案 5：只保存 `document_id` 作为缓存键

源文档修改后仍然命中旧缓存，造成内容和结构不一致。

### 失败方案 6：用平滑滚动定位大树节点

长文档中平滑滚动会产生较长的合成动画，使用即时定位更稳：

```javascript
el.scrollIntoView({ block: 'center', behavior: 'instant' })
```

## 九、通用实施顺序

1. 统计节点数量、HTML 大小、图片数量、首次解析耗时。
2. 为解析结果增加版本化后端磁盘缓存。
3. 增加独立解析状态和状态接口。
4. 使用单线程后台预解析。
5. 前端结构数据改成 `shallowRef + markRaw`。
6. 勾选状态改成 `Set`，批量更新改为 `setCheckedKeys`。
7. 预览改成首屏分段加载和滚动追加。
8. 建立预览节点索引并做增量高亮。
9. 全部展开/折叠改为 `requestAnimationFrame` 分帧执行。
10. 如果仍有大量 DOM，再替换为虚拟树或虚拟列表。

## 十、验收清单

- [ ] 首次打开文档不会在主线程同步解析全部内容。
- [ ] 文档列表能显示解析状态。
- [ ] 缓存命中条件包含源文件版本和缓存版本。
- [ ] 缓存损坏或过期时能自动重新解析。
- [ ] 预览首屏只创建有限节点。
- [ ] 滚动加载不会重复插入样式和外层容器。
- [ ] 结构树展开/折叠不会长时间阻塞主线程。
- [ ] 勾选一次不会深度遍历整个结构对象。
- [ ] 批量勾选只触发一次组件批量更新。
- [ ] 预览高亮使用节点索引，不反复全 DOM 查询。
- [ ] 图片不会每次滚动都重新打开 DOCX ZIP。
- [ ] 后端缓存和浏览器缓存都有明确失效策略。
- [ ] 修改前已备份，后端语法、接口和前端构建均通过。

## 十一、本项目验证结果

本项目大型白皮书约有 5,101 个节点，其中包含标题、正文、表格、列表和图片。已验证有效的优化组合为：

```text
后台单线程预解析
+ 后端本地持久化缓存
+ 图片提前提取
+ shallowRef/markRaw
+ Set 保存勾选 ID
+ 批量 setCheckedKeys
+ requestAnimationFrame 合并同步
+ 预览首屏分段加载
+ 结构树展开分帧执行
```

这套组合比单纯把数据迁移到 IndexedDB 更有效，因为真正的瓶颈主要来自：

```text
深度响应式更新
+ 大量 DOM 创建
+ 同步布局和绘制
+ 组件级批量事件
```

而不是单纯的文件读取速度。
