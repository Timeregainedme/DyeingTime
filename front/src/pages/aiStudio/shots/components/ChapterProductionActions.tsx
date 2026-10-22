/**
 * 章节制作四段式操作栏。
 *
 * 为什么独立成组件：分镜、资产、提示词、出图是四个可独立重试的阶段，
 * 不应该再串成一条“一键全流程”的长链。这里只负责按钮、阶段状态和弹窗，
 * 具体的任务执行仍复用既有后端接口。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Checkbox,
  Input,
  Modal,
  Progress,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import {
  FilmService,
  ShotLinkedAssetItem,
  ScriptProcessingService,
  StudioChaptersService,
  StudioImageTasksService,
  StudioShotDetailsService,
  StudioShotsService,
} from '../../../../services/generated'

const { Text } = Typography

const ASSET_ORDER = ['costume', 'scene', 'prop', 'character'] as const
type AssetType = (typeof ASSET_ORDER)[number]
const ASSET_LABEL: Record<AssetType, string> = {
  costume: '服装',
  scene: '场景',
  prop: '道具',
  character: '角色',
}
const FRAME_TYPES = ['first', 'key', 'last'] as const
type TargetRatio = '16:9' | '4:3' | '1:1' | '3:4' | '9:16' | '21:9' | '3:2' | '2:3'
type FrameType = (typeof FRAME_TYPES)[number]

type ProductionStatus = {
  shots: number
  candidates: { pending: number; linked: number; ignored: number }
  assets: Record<string, number>
  character_actor_missing: string[]
  asset_prompt_snapshots: Record<string, number>
  frame_prompts: Record<string, number>
  frame_images: Record<string, number>
}

type PromptItem = {
  key: string
  assetType: AssetType
  assetId: string
  assetName: string
  prompt: string
}

export interface ChapterProductionActionsProps {
  projectId: string
  chapterId: string
  shots: Array<{ id: string; index: number; title: string }>
  sourceText: string
  onRefresh: () => Promise<void> | void
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function waitTask(taskId: string, onProgress?: (value: number) => void) {
  const started = Date.now()
  while (Date.now() - started < 15 * 60 * 1000) {
    const resp = await FilmService.getTaskStatusApiV1FilmTasksTaskIdStatusGet({ taskId })
    const data = (resp.data ?? {}) as { status?: string; progress?: number; error?: string }
    onProgress?.(Number(data.progress ?? 0))
    if (data.status === 'succeeded') return
    if (data.status === 'failed' || data.status === 'cancelled') {
      throw new Error(data.error || `任务状态 ${data.status}`)
    }
    await sleep(2000)
  }
  throw new Error('任务超时（15 分钟）')
}

const emptyStatus: ProductionStatus = {
  shots: 0,
  candidates: { pending: 0, linked: 0, ignored: 0 },
  assets: {},
  character_actor_missing: [],
  asset_prompt_snapshots: {},
  frame_prompts: {},
  frame_images: {},
}

const ChapterProductionActions: React.FC<ChapterProductionActionsProps> = ({
  projectId,
  chapterId,
  shots,
  sourceText,
  onRefresh,
}) => {
  const [status, setStatus] = useState<ProductionStatus>(emptyStatus)
  const [running, setRunning] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const [promptOpen, setPromptOpen] = useState(false)
  const [promptRunning, setPromptRunning] = useState(false)
  const [promptItems, setPromptItems] = useState<PromptItem[]>([])
  const [promptDrafts, setPromptDrafts] = useState<Record<string, string>>({})
  const [imageOpen, setImageOpen] = useState(false)
  const [imageRunning, setImageRunning] = useState(false)
  const [imageAsset, setImageAsset] = useState(true)
  const [imageFrame, setImageFrame] = useState(false)
  const [framePromptRunning, setFramePromptRunning] = useState(false)

  const totalAssets = useMemo(
    () => ASSET_ORDER.reduce((sum, type) => sum + Number(status.assets[type] ?? 0), 0),
    [status.assets],
  )
  const totalSnapshots = useMemo(
    () => ASSET_ORDER.reduce((sum, type) => sum + Number(status.asset_prompt_snapshots[type] ?? 0), 0),
    [status.asset_prompt_snapshots],
  )
  const totalFramePrompts = useMemo(
    () => FRAME_TYPES.reduce((sum, type) => sum + Number(status.frame_prompts[type] ?? 0), 0),
    [status.frame_prompts],
  )

  const reloadStatus = useCallback(async () => {
    try {
      const resp = await StudioChaptersService.getChapterProductionStatusApiV1StudioChaptersChapterIdProductionStatusGet(
        { chapterId },
      )
      const data = (resp.data ?? {}) as Partial<ProductionStatus>
      setStatus({
        ...emptyStatus,
        ...data,
        candidates: { ...emptyStatus.candidates, ...(data.candidates ?? {}) },
        assets: data.assets ?? {},
        asset_prompt_snapshots: data.asset_prompt_snapshots ?? {},
        frame_prompts: data.frame_prompts ?? {},
        frame_images: data.frame_images ?? {},
        character_actor_missing: data.character_actor_missing ?? [],
      })
    } catch {
      // 状态接口失败不阻断主流程
    }
  }, [chapterId])

  useEffect(() => {
    void reloadStatus()
  }, [reloadStatus, shots.length])

  const runDivide = async () => {
    if (!sourceText.trim()) {
      message.warning('章节缺少原文，无法提取分镜')
      return
    }
    setRunning('divide')
    setProgress(0)
    try {
      const resp = await ScriptProcessingService.divideScriptAsyncApiV1ScriptProcessingDivideAsyncPost({
        requestBody: { chapter_id: chapterId, script_text: sourceText, write_to_db: true },
      })
      const taskId = String((resp.data as { task_id?: string } | undefined)?.task_id ?? '')
      if (!taskId) throw new Error('未返回任务 ID')
      await waitTask(taskId, setProgress)
      message.success('分镜提取完成')
      await onRefresh()
      await reloadStatus()
    } catch (error) {
      message.error(`分镜提取失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setRunning('')
    }
  }

  const runExtractAssets = async (linkOnly: boolean) => {
    if (shots.length === 0) {
      message.warning('请先提取分镜')
      return
    }
    setRunning(linkOnly ? 'link' : 'extract')
    setProgress(0)
    try {
      if (!linkOnly) {
        const resp = await ScriptProcessingService.extractScriptAsyncApiV1ScriptProcessingExtractAsyncPost({
          requestBody: {
            project_id: projectId,
            chapter_id: chapterId,
            script_division: {},
            refresh_cache: true,
          },
        })
        const taskId = String((resp.data as { task_id?: string } | undefined)?.task_id ?? '')
        if (!taskId) throw new Error('未返回任务 ID')
        await waitTask(taskId, setProgress)
      }
      const created =
        await StudioShotsService.batchCreateAssetsFromCandidatesApiV1StudioShotsExtractedCandidatesBatchCreateAssetsPost(
          { requestBody: { chapter_id: chapterId, link_only: linkOnly } },
        )
      const data = (created.data ?? {}) as {
        created?: unknown[]
        linked?: unknown[]
        skipped?: unknown[]
      }
      message.success(
        `${linkOnly ? '重新关联' : '资产提取'}完成：新建 ${data.created?.length ?? 0} / 关联 ${
          data.linked?.length ?? 0
        } / 跳过 ${data.skipped?.length ?? 0}`,
      )
      await onRefresh()
      await reloadStatus()
    } catch (error) {
      message.error(`${linkOnly ? '重新关联' : '提取资产'}失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setRunning('')
    }
  }

  const runPromptRender = async (force = false) => {
    setPromptRunning(true)
    try {
      const items: PromptItem[] = []
      for (const assetType of ASSET_ORDER) {
        const resp =
          await StudioImageTasksService.batchRenderAssetImagePromptsApiV1StudioImageTasksAssetsAssetTypeBatchRenderPromptsPost(
            {
              assetType,
              requestBody: { project_id: projectId, only_missing: !force },
            },
          )
        const data = (resp.data ?? {}) as {
          items?: Array<{
            asset_id: string
            asset_name?: string
            prompt?: string
            asset_type?: string
          }>
        }
        for (const item of data.items ?? []) {
          const key = `${assetType}:${item.asset_id}`
          items.push({
            key,
            assetType,
            assetId: item.asset_id,
            assetName: item.asset_name || item.asset_id,
            prompt: item.prompt || '',
          })
        }
      }
      setPromptItems(items)
      setPromptDrafts(Object.fromEntries(items.map((item) => [item.key, item.prompt])))
      setPromptOpen(true)
      if (items.length === 0) {
        message.info('所有资产都已有提示词审核稿；可点“重新渲染全部提示词”强制刷新')
      }
      await reloadStatus()
    } catch (error) {
      message.error(`生成提示词失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setPromptRunning(false)
    }
  }

  const savePromptDraft = async (item: PromptItem) => {
    const prompt = (promptDrafts[item.key] ?? '').trim()
    if (!prompt) {
      message.warning('提示词不能为空')
      return
    }
    try {
      await StudioImageTasksService.updateAssetPromptSnapshotApiV1StudioImageTasksAssetsAssetTypePromptSnapshotsAssetIdPatch(
        { assetType: item.assetType, assetId: item.assetId, requestBody: { prompt } },
      )
      setPromptItems((prev) => prev.map((row) => (row.key === item.key ? { ...row, prompt } : row)))
      message.success(`已保存「${item.assetName}」的提示词`)
      await reloadStatus()
    } catch (error) {
      message.error(`保存失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }

  const saveAllDrafts = async () => {
    const changed = promptItems.filter((item) => {
      const draft = (promptDrafts[item.key] ?? '').trim()
      return draft && draft !== item.prompt
    })
    for (const item of changed) {
      const prompt = (promptDrafts[item.key] ?? '').trim()
      if (!prompt) continue
      await StudioImageTasksService.updateAssetPromptSnapshotApiV1StudioImageTasksAssetsAssetTypePromptSnapshotsAssetIdPatch(
        { assetType: item.assetType, assetId: item.assetId, requestBody: { prompt } },
      )
    }
    if (changed.length > 0) {
      setPromptItems((prev) =>
        prev.map((row) => ({
          ...row,
          prompt: (promptDrafts[row.key] ?? row.prompt).trim() || row.prompt,
        })),
      )
      message.success(`已保存 ${changed.length} 条提示词修改`)
      await reloadStatus()
    }
  }

  const runFramePrompts = async () => {
    if (shots.length === 0) {
      message.warning('请先提取分镜')
      return
    }
    setFramePromptRunning(true)
    try {
      const taskIds: string[] = []
      for (const shot of shots) {
        for (const frameType of FRAME_TYPES) {
          const resp = await FilmService.createShotFramePromptTaskApiV1FilmTasksShotFramePromptsPost({
            requestBody: { shot_id: shot.id, frame_type: frameType },
          })
          const taskId = String((resp.data as { task_id?: string } | undefined)?.task_id ?? '')
          if (taskId) taskIds.push(taskId)
        }
      }
      await Promise.all(taskIds.map((taskId) => waitTask(taskId)))
      message.success(`分镜帧提示词已生成：${taskIds.length} 个任务`)
      await reloadStatus()
    } catch (error) {
      message.error(`分镜帧提示词生成失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setFramePromptRunning(false)
    }
  }

  const runImageGeneration = async () => {
    if (!imageAsset && !imageFrame) {
      message.warning('请至少选择一种图片')
      return
    }
    setImageRunning(true)
    try {
      let assetTasks = 0
      if (imageAsset) {
        for (const assetType of ASSET_ORDER) {
          try {
            const resp =
              await StudioImageTasksService.createBatchAssetImageTasksApiV1StudioImageTasksAssetsBatchImageTasksPost(
                {
                  requestBody: {
                    project_id: projectId,
                    asset_type: assetType,
                    use_prompt_snapshots: true,
                  },
                },
              )
            const data = (resp.data ?? {}) as { tasks?: unknown[] }
            assetTasks += data.tasks?.length ?? 0
          } catch (error) {
            message.warning(
              `${ASSET_LABEL[assetType]}图提交失败：${error instanceof Error ? error.message : String(error)}`,
            )
          }
        }
      }

      let frameTasks = 0
      if (imageFrame) {
        for (const shot of shots) {
          const detailResp = await StudioShotDetailsService.getShotDetailApiV1StudioShotDetailsShotIdGet({
            shotId: shot.id,
          })
          const detail = (detailResp.data ?? {}) as {
            first_frame_prompt?: string
            key_frame_prompt?: string
            last_frame_prompt?: string
            override_video_ratio?: string | null
          }
          const targetRatio = (detail.override_video_ratio || '9:16') as TargetRatio
          const basePrompts: Record<FrameType, string> = {
            first: detail.first_frame_prompt ?? '',
            key: detail.key_frame_prompt ?? '',
            last: detail.last_frame_prompt ?? '',
          }
          const assetsResp = await StudioShotsService.listShotLinkedAssetsApiV1StudioShotsShotIdLinkedAssetsGet({
            shotId: shot.id,
            pageSize: 100,
          })
          const assetsPayload = (assetsResp.data ?? {}) as {
            items?: ShotLinkedAssetItem[]
          }
          const assets: ShotLinkedAssetItem[] = assetsPayload.items ?? []
          for (const frameType of FRAME_TYPES) {
            const basePrompt = basePrompts[frameType].trim()
            if (!basePrompt) continue
            const rendered =
              await StudioImageTasksService.renderShotFramePromptApiV1StudioImageTasksShotShotIdFrameRenderPromptPost(
                {
                  shotId: shot.id,
                  requestBody: { frame_type: frameType, prompt: basePrompt, images: assets },
                },
              )
            const renderedPrompt = String((rendered.data as { rendered_prompt?: string } | undefined)?.rendered_prompt ?? '')
            if (!renderedPrompt) continue
            await StudioImageTasksService.createShotFrameImageGenerationTaskApiV1StudioImageTasksShotShotIdFrameImageTasksPost(
              {
                shotId: shot.id,
                requestBody: {
                  frame_type: frameType,
                  prompt: renderedPrompt,
                  images: assets,
                  target_ratio: targetRatio,
                },
              },
            )
            frameTasks += 1
          }
        }
      }

      message.success(`已提交图片任务：资产图 ${assetTasks} / 分镜帧图 ${frameTasks}`)
      setImageOpen(false)
      await reloadStatus()
    } catch (error) {
      message.error(`生成图片失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setImageRunning(false)
    }
  }

  const promptColumns = [
    {
      title: '类型',
      dataIndex: 'assetType',
      width: 90,
      render: (value: AssetType) => <Tag color="blue">{ASSET_LABEL[value]}</Tag>,
    },
    { title: '名称', dataIndex: 'assetName', width: 160 },
    {
      title: '提示词',
      dataIndex: 'prompt',
      render: (value: string) => (
        <Text ellipsis style={{ maxWidth: 420 }}>
          {value}
        </Text>
      ),
    },
    {
      title: '操作',
      width: 90,
      render: (_: unknown, item: PromptItem) => (
        <Button size="small" type="link" onClick={() => void savePromptDraft(item)}>
          保存
        </Button>
      ),
    },
  ]

  return (
    <>
      <Space wrap>
        <Tooltip title={shots.length > 0 ? '已有分镜，请先清空后重新提取' : '只切分镜，不提取资产、不写提示词'}>
          <span>
            <Button loading={running === 'divide'} disabled={!!running || shots.length > 0} onClick={() => void runDivide()}>
              提取分镜
            </Button>
          </span>
        </Tooltip>
        <Button loading={running === 'extract'} disabled={!!running || shots.length === 0} onClick={() => void runExtractAssets(false)}>
          提取资产
        </Button>
        <Button loading={running === 'link'} disabled={!!running || shots.length === 0} onClick={() => void runExtractAssets(true)}>
          重新关联
        </Button>
        <Button
          loading={promptRunning || framePromptRunning}
          disabled={!!running || totalAssets === 0}
          onClick={() => void runPromptRender(false)}
        >
          生成提示词
        </Button>
        <Button
          disabled={!!running || (totalSnapshots === 0 && totalFramePrompts === 0)}
          onClick={() => setImageOpen(true)}
        >
          生成图片
        </Button>
      </Space>

      <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
        <Tag>分镜 {status.shots}</Tag>
        <Tag color={status.candidates.pending > 0 ? 'orange' : 'default'}>
          候选待处理 {status.candidates.pending}
        </Tag>
        <Tag>资产 {totalAssets}</Tag>
        <Tag color={totalSnapshots > 0 ? 'green' : 'default'}>提示词 {totalSnapshots}</Tag>
        <Tag color={totalFramePrompts > 0 ? 'green' : 'default'}>帧提示词 {totalFramePrompts}</Tag>
        {status.character_actor_missing.length > 0 ? (
          <Tag color="orange">角色缺演员：{status.character_actor_missing.join('、')}</Tag>
        ) : null}
      </div>

      {running === 'divide' || running === 'extract' ? (
        <div className="mt-2">
          <Progress percent={progress} size="small" status="active" />
        </div>
      ) : null}

      <Modal
        title="提示词审核"
        open={promptOpen}
        width={960}
        onCancel={() => setPromptOpen(false)}
        footer={[
          <Button key="close" onClick={() => setPromptOpen(false)}>
            关闭
          </Button>,
          <Button key="rerender" onClick={() => void runPromptRender(true)}>
            重新渲染全部提示词
          </Button>,
          <Button
            key="frame"
            loading={framePromptRunning}
            onClick={() => void runFramePrompts()}
          >
            生成分镜帧提示词（可选）
          </Button>,
          <Button
            key="images"
            type="primary"
            onClick={() => {
              void (async () => {
                try {
                  await saveAllDrafts()
                  setPromptOpen(false)
                  setImageOpen(true)
                } catch (error) {
                  message.error(`保存提示词失败：${error instanceof Error ? error.message : String(error)}`)
                }
              })()
            }}
          >
            去生成图片
          </Button>,
        ]}
      >
        <Alert
          type="info"
          showIcon
          message="多参考图视频只依赖资产参考图，分镜帧提示词不是硬前置"
          description="资产图提示词按服装 → 场景 → 道具 → 角色渲染；角色缺演员绑定时会在状态栏提示。"
          className="mb-3"
        />
        <Table
          size="small"
          rowKey="key"
          dataSource={promptItems}
          columns={promptColumns}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (item: PromptItem) => (
              <Input.TextArea
                rows={6}
                value={promptDrafts[item.key] ?? item.prompt}
                onChange={(event) =>
                  setPromptDrafts((prev) => ({ ...prev, [item.key]: event.target.value }))
                }
              />
            ),
          }}
        />
      </Modal>

      <Modal
        title="生成图片"
        open={imageOpen}
        onCancel={() => setImageOpen(false)}
        onOk={() => void runImageGeneration()}
        confirmLoading={imageRunning}
        okText="确认生成"
      >
        <Alert
          type="warning"
          showIcon
          message="生成图片会调用图片模型并产生费用"
          description="只会为缺少图片的资产提交；已有图片不会重复生成。"
          className="mb-3"
        />
        {imageAsset && status.character_actor_missing.length > 0 ? (
          <Alert
            type="warning"
            showIcon
            className="mb-3"
            message={`以下角色未绑定演员，角色图会缺少身份参考：${status.character_actor_missing.join('、')}`}
          />
        ) : null}
        <Space direction="vertical">
          <Checkbox checked={imageAsset} onChange={(event) => setImageAsset(event.target.checked)}>
            资产图（服装 → 场景 → 道具 → 角色）
          </Checkbox>
          <Checkbox checked={imageFrame} onChange={(event) => setImageFrame(event.target.checked)}>
            分镜帧图（可选；多参考图视频不需要）
          </Checkbox>
        </Space>
      </Modal>
    </>
  )
}

export default ChapterProductionActions
