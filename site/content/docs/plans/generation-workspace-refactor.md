# 生成准备架构重构计划

## 背景

当前图片生成、视频生成、资产图片生成都逐步暴露出同一类问题：

- 基础真值与最终提交内容混用
- 预览与提交使用的上下文不完全一致
- 页面内部状态分散，容易出现 `stale / loading / submit` 语义混乱

为避免在多个入口重复修同类问题，生成链需要统一收敛到同一套“生成准备”架构。

## 目标模型

统一使用四层模型：

1. `Base Draft`
   - 可持久化、可编辑的业务真值
2. `Context`
   - 本次生成的动态上下文
3. `Derived Preview`
   - 基于 `Base Draft + Context` 推导出的预览结果
4. `Submission Payload`
   - 真正提交给模型的最终载荷

## 范围

本次计划覆盖：

1. 分镜帧图片生成链
2. 视频提示词预览与提交链
3. 资产图片生成链

本次不纳入：

1. 任务中心
2. 脚本处理类任务
3. 分镜编辑页提取确认流

## 已完成阶段

### Phase 1：shared + frame 样板

- 新增 `studio/generation/shared`
- 新增 `studio/generation/frame`
- 关键帧图片链先按 `Base / Context / Derived / Submission` 拆分
- 旧 API 路径保持不变，先替换内部服务调用

### Phase 2：前端统一 draft hook

- 新增 `useGenerationDraft`
- 分镜帧图片弹窗先接入统一状态机

### Phase 3：视频生成链迁移

- 视频预览与提交统一迁到 `derive -> submit`
- 保证 readiness、preview、submit 共享同一套上下文规则

### Phase 4：资产图片链迁移

- 角色 / 演员 / 场景 / 道具 / 服装图片生成统一收敛

## 当前进展

- 已完成：关键帧图片最终提示词渲染与提交链统一 render 兜底
- 已完成：`generation/shared + generation/frame` 服务目录搭建
- 已完成：前端 `useGenerationDraft` 抽象，并接入关键帧提示词预览与提交链
- 已完成：`generation/video` 服务目录搭建，视频 preview / submit 共享同一份 reference context
- 已完成：`generation/asset_image` 服务目录搭建，角色 / 演员 / 场景 / 道具 / 服装图片统一接入 render / submit 结构
- 已完成：`AssetEditPageBase` 接入 `useGenerationDraft`，资产图片前端已统一到 draft / context / derived / submit 语义

## 剩余收尾

当前主链迁移已完成，后续仅剩小规模收尾事项：

1. 继续压缩 `ChapterStudio` 内部围绕关键帧 / 视频 draft 的局部辅助逻辑
2. 在后续合适时机处理仓库现有前端类型遗留问题
3. 结合后续需求再评估是否需要继续抽离更通用的生成 UI 组件
