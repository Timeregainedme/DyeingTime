---
title: "后端说明"
weight: 3
description: "理解后端路由主轴、分层结构与服务定位。"
---

后端位于 `backend/`，使用 FastAPI、SQLAlchemy、LangChain / LangGraph 构建。
当前已经完成一轮“**路由层瘦身 + service 分层**”整理，整体结构比早期原型期更清晰。

核心分层：

- `app/main.py`：应用入口
- `app/api/v1/`：路由层
- `app/services/`：业务服务层
- `app/models/`：ORM 模型
- `app/schemas/`：请求响应模型
- `app/chains/`：Agent、Prompt 与工作流

## 路由主轴

当前主要接口聚焦在：

- `studio`：项目、章节、分镜、文件、提示词、时间线等主业务
- `llm`：模型与供应商能力
- `film`：生成相关接口
- `script-processing`：脚本处理与提取能力

## 服务层定位

`app/services/` 负责承接业务逻辑，而不是把复杂逻辑全部塞进路由中。  
像分镜草稿拼装、图片任务构建、模型解析等能力，都已经下沉到了 service 层。

当前可以按下面的方式理解：

- `services/common`
  - 通用校验、通用 CRUD、公共错误文案
- `services/studio`
  - 项目、章节、分镜、文件、图片任务等 Studio 主链路
- `services/llm`
  - Provider、Model、Settings 管理
- `services/film`
  - 视频生成、分镜帧提示词任务等编排逻辑

## 响应与测试

后端接口当前统一使用 `ApiResponse` 响应壳，并约定：

- 创建：`created_response(...)`
- 普通成功：`success_response(...)`
- 空响应：`empty_response()`
- 分页：`paginated_response(...)`

测试入口也已经统一，既可以在 `backend/` 目录执行，也可以在仓库根目录执行。

推荐命令：

```bash
cd backend
uv run pytest -q
```

如果只做快速验证，也可以优先运行接口响应壳测试与 service 层测试。
