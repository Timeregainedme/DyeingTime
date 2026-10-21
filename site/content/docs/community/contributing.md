---
title: "贡献指南"
weight: 1
description: "参与 DyeingTime 代码和文档协作的起点。"
---

> 仓库根目录的 [CONTRIBUTING.md](https://github.com/Timeregainedme/dyeingtime/blob/main/CONTRIBUTING.md)
> 是完整版本，本文是同一套约定的站点侧摘要。

## 贡献方式

- 提交 Issue 反馈问题或提出建议
- 提交 Pull Request 改进代码或文档

## 开发前建议

- 先阅读项目结构与本地开发文档
- 优先沿用现有前后端分层与命名方式
- 同步更新相关文档
- 完整规范见仓库根目录的 [AGENTS.md](https://github.com/Timeregainedme/dyeingtime/blob/main/AGENTS.md)

## 提交前建议检查

- 后端是否能正常启动，`uv run pytest -q` 是否通过
- 前端是否能正常访问，`pnpm exec tsc --noEmit` 是否通过
- 如果修改了接口，是否更新 OpenAPI 生成代码（`pnpm run openapi:update`）
- 如果改了 `backend/go/`，是否 `go build ./... && go vet ./... && go test ./...` 通过
- 如果改了站点内容，是否至少本地预览过一次 `site/`

## 提交信息规范

首行必须为 `[类型] 摘要`，类型取自：

```text
feat  fix  docs  style  refactor  perf  test  chore  ci  build  revert
```

本地校验钩子（一次性启用）：

```bash
git config core.hooksPath .githooks
```

CI 会对 PR 与直推 `main` 校验同一份规则，`.githooks/commit-msg` 与
`.github/workflows/commit-messages.yml` 的 `PATTERN` 必须保持一致。

## 文档协作建议

当你修改以下内容时，建议同步更新 `site/` 文档：

- 启动方式
- 目录结构
- 接口与数据模型
- 状态语义与页面职责边界
- 部署与运维方式

文档归属必须严格区分，不要混写：

| 栏目 | 回答什么问题 | 位置 |
| --- | --- | --- |
| `architecture` | 现在是什么（已生效的实现与边界） | `site/content/docs/architecture/` |
| `plans` | 接下来做什么（正在推进的改造） | `site/content/docs/plans/` |
| `guide` | 怎么做（操作说明、开发流程） | `site/content/docs/guide/` |
| `reference` | 查什么（稳定参考资料） | `site/content/docs/reference/` |

已固化的历史 release note（`site/content/blog/`）未经明确要求不得修改。

## 安全问题

不要在 Issue 或 PR 中公开 API Key、密码、Cookie、数据库连接串等敏感信息。
如发现漏洞，请私下反馈，修复后再公开讨论。
