# 贡献指南

感谢关注 DyeingTime。本文件说明如何参与代码与文档协作。

> 项目开发规范（后端分层职责、注释要求、状态语义、文档归属）见
> [AGENTS.md](./AGENTS.md)，它对所有代码变更同样生效。

## 贡献方式

- **Issue**：反馈缺陷、提出功能建议、讨论设计取舍
- **Pull Request**：改进代码或文档

## 快速上手

```bash
git clone https://github.com/Timeregainedme/dyeingtime.git
cd dyeingtime

# 后端
cd backend && cp .env.example .env && uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000

# 前端（另开一个终端）
cd front && pnpm install && pnpm dev
```

## 分支与提交

- 从 `main` 切出功能分支：`feat/xxx`、`fix/xxx`、`docs/xxx`
- 提交信息**首行必须**是 `[类型] 摘要`，类型取自：

  ```text
  feat  fix  docs  style  refactor  perf  test  chore  ci  build  revert
  ```

- 启用本地校验钩子（一次性）：

  ```bash
  git config core.hooksPath .githooks
  ```

  CI 会对 PR 与直推 `main` 校验同一份规则，`.githooks/commit-msg` 与
  `.github/workflows/commit-messages.yml` 的 `PATTERN` 必须保持一致。

## 提交前必跑

```bash
# 1. 后端测试
cd backend && uv run pytest -q

# 2. OpenAPI 契约比对（接口有变更时）
cd backend && uv run python scripts/check_openapi_contract.py

# 3. 前端类型与测试
cd front && pnpm exec tsc --noEmit && pnpm test

# 4. Go 控制面（改了 backend/go 时）
cd backend/go && go build ./... && go vet ./... && go test ./...
```

## 变更约定

### 后端

- 严格区分 `api` 层（收参、鉴权、响应组织）与 `service` 层（业务逻辑、状态流转、数据编排）
- 新增或改动的函数、类必须补注释：至少说明「做什么」与「为什么存在」；
  复杂函数补充参数、返回值与关键内部逻辑说明
- 涉及业务实体的读写必须走 `app/api/scoping.py` 的工作区归属校验，
  跨工作区统一返回 404，不要返回 403
- 敏感字段（供应商密钥）用 `EncryptedString` 类型，不要自己拼加解密

### 前端

- 调用后端接口统一走 OpenAPI generated client（`front/src/services/generated/`），
  不要新增手写 service 封装
- 样式重复超过一次即抽离为可复用组件或公共样式
- 保持「分镜编辑页 = 准备」「分镜工作室 = 生成」「任务中心 = 通用任务面板」的职责边界
- 状态展示必须区分三类：信息确认状态（`shot.status`）、运行时任务状态、视频生成准备度

### 契约与文档

- **任何后端接口变更后**，必须重新生成前端请求与类型：

  ```bash
  cd front && pnpm run openapi:update
  ```

- 状态语义、页面职责边界、系统结构发生变化时，同步更新：

  | 内容归属 | 位置 |
  | --- | --- |
  | 当前真实实现与边界 | `site/content/docs/architecture/` |
  | 正在推进的方案与任务 | `site/content/docs/plans/` |
  | 操作说明与开发流程 | `site/content/docs/guide/` |
  | 稳定参考资料 | `site/content/docs/reference/` |
  | 版本发布说明 | `site/content/blog/` |

- 已固化的历史 release note 未经明确要求不得修改

## 数据库迁移

- 迁移追加为 `backend/sql/` 下**下一个未占用序号**的新文件，不要改动已应用的编号
- 脚本写成幂等形式（`IF NOT EXISTS` / `information_schema` 判定）
- 同时更新 SQLAlchemy 模型（`backend/app/models/`）与 `backend/app/core/db.py` 的建表注册

## 文档站

```bash
cd site && hugo server
```

改动站点内容后请至少本地预览一次。

## 安全问题

**不要**在 Issue 或 PR 中公开 API Key、密码、Cookie、数据库连接串等敏感信息。
如发现漏洞，请通过仓库的私密渠道私下反馈，修复后再公开讨论。
