\# AI Coding Rules — Word Format Batch Editor



\## MUST (Hard Constraints)

1\. NEVER add dependencies not in requirements.txt/package.json without explicit user approval.

2\. NEVER modify start.bat, stop.bat, config.yaml structure, or PyInstaller packaging logic.

3\. NEVER modify files under storage/original/. All output goes to storage/processed/.

4\. NEVER use external CDN, remote APIs, or online resources. Must work fully offline.

5\. NEVER break backward compatibility of schemas/models. Provide migration if fields change.

6\. ALL file I/O, XML parsing, and network calls MUST have try-except with logger.error.

7\. ALL paths MUST use pathlib.Path. NEVER use string concatenation for paths.

8\. ALL user input MUST be validated via Pydantic models. NEVER trust raw dicts.

9\. ALL custom\_expression rules MUST use AST whitelist evaluation. NEVER use eval/exec.

10\. ALL code comments in English. ALL user-facing text in Chinese via i18n keys.



\## SHOULD (Strong Preferences)

1\. Use async/await consistently. Wrap blocking calls in run\_in\_executor.

2\. Use Pydantic v2 syntax (model\_config, not class Config).

3\. Use <script setup lang="ts"> with typed props and emits. No Options API.

4\. Use scoped SCSS with variables from variables.scss.

5\. Prefer f-strings over % formatting or .format().

6\. Keep single files under 500 lines. Split when exceeding.

7\. Follow Conventional Commits (feat/fix/docs/refactor/test/chore) in English.



\## Response Protocol

Adapt response depth by task level:



\*\*L1 (typo, comment, CSS tweak):\*\* Fix directly → Output change summary.

\*\*L2 (bug fix, small feature):\*\* Impact analysis → Fix → Change summary.

\*\*L3 (engine/model/API/deploy change):\*\* Impact analysis → Tests → Fix → Change summary → List items requiring human verification.



\### Change Summary Format (Always include after modifications)

## 修改前自动备份规则

### 触发条件
在修改任何已有文件之前（写入新文件不需要备份）。

### 执行步骤
1. 在项目根目录下创建 `.backup/` 目录（若不存在）。
2. 生成时间戳目录名：格式为 `YYYY-MM-DD_HHmmss`。
3. 将开始修改操作前的所有代码文档按原始相对路径复制到 `.backup/{时间戳}/` 下。
4. 备份完成后，在回复中输出一行确认：
   `✅ 已备份: .backup/{时间戳}/{文件相对路径}`
5. 然后再执行实际的文件修改。

### 清理策略
每次备份前检查 `.backup/` 下的子目录数量，若超过 20 个，删除最旧的目录。


