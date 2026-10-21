# 归档区

本目录存放**历史评审记录与一次性方案文档**，仅供追溯「为什么变成今天这样」。

> ⚠️ **归档文档不是现行依据。**
> 这里的结论可能已被后续实现推翻，请以以下位置为准：
>
> - 当前实现与边界 → `site/content/docs/architecture/`
> - 正在推进的计划 → `site/content/docs/plans/`
> - 操作与接入方式 → `site/content/docs/guide/`
> - 稳定参考资料 → `site/content/docs/reference/`
>
> 归档于 2026-10-21。

## 目录

| 文件 | 内容 | 归档原因 |
| --- | --- | --- |
| `审阅报告-426f9ab.md` | `58d9a33` → `426f9ab` 的一次性代码评审，42 条缺陷及逐条闭环 | 结论已闭环，对后续开发者无增量价值 |
| `技术评审报告-2026-10-13.md` | 2026-10-13 的三角色并行技术评审，判定为 NO-GO / C 级 | 其中「零鉴权 / Redis 无密码 / MySQL root@%」等结论**已被后续实现推翻**，保留会误导读者以为系统仍不安全 |
| `提示词改造方案.md` | 提示词链路的 9 条发现与组合推荐（决策版） | 决策点从未定稿，且已被 `site/content/docs/architecture/prompt-templates.md` 与 `site/content/docs/plans/prompt-pipeline-optimization.md` 取代 |

## 归档时的处理

归档文件均已做以下脱敏，保留可复现的结构信息，去除本机路径与上游旧 fork 地址：

- 本地开发路径 → `<local-workspace>` / `<reference-impl>` / `<repo-root>`
- 生产主机别名 → `<server>`
