/**
 * 项目配置面板。
 *
 * P1 只做只读展示 + 跳转旧版设置：
 *   - 模型快照、风格锁定、并发配置属于 P2，本阶段不伪造编辑能力；
 *   - 旧版设置页仍可编辑，用新标签页打开，工作台当前节点不会丢失。
 */
import { ExternalLink, Settings2 } from 'lucide-react'
import type { ProjectRead } from '../../../services/generated'
import { Button } from '../../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { InfoGrid, type InfoItem } from '../components/InfoGrid'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelError, PanelLoading, StageNote } from '../components/PanelStates'

export function ProjectConfigPanel({
  projectId,
  project,
  loading,
  error,
  onRetry,
}: {
  projectId: string
  project?: ProjectRead
  loading: boolean
  error: unknown
  onRetry: () => void
}) {
  if (loading) return <PanelLoading lines={6} />
  if (error || !project) {
    return (
      <PanelError
        message={error instanceof Error ? error.message : '项目配置加载失败'}
        onRetry={onRetry}
      />
    )
  }

  const projectItems: InfoItem[] = [
    { label: '项目名称', value: project.name },
    { label: '题材', value: project.style },
    { label: '表现形式', value: project.visual_style },
    { label: '简介', value: project.description || '—' },
    { label: '随机种子', value: project.seed ?? 0 },
    { label: '统一风格', value: project.unify_style ? '是' : '否' },
  ]

  const generationItems: InfoItem[] = [
    { label: '默认视频比例', value: project.default_video_ratio || '未设置' },
    { label: '默认图片比例', value: project.default_image_ratio || '未设置' },
    { label: '视频分辨率', value: project.default_video_resolution || '供应商默认' },
    { label: '图片分辨率档位', value: project.default_image_resolution_profile || '供应商默认' },
    {
      label: '台词音频作参考',
      value: project.use_dialog_audio_as_reference ? '开启' : '关闭',
    },
  ]

  return (
    <div className="space-y-4">
      <PanelHeader
        title="项目配置"
        description="项目级基础信息与生成参数。P1 只读展示，编辑仍走旧版项目设置。"
        actions={
          <LegacyLink href={`/projects/${projectId}?tab=settings`}>
            <ExternalLink className="h-3.5 w-3.5" />
            旧版项目设置
          </LegacyLink>
        }
      />

      <StageNote stage="P2">
        项目模型快照、风格锁定、默认并发与逐项内嵌编辑将在 P2 落地；当前参数以旧版设置为准。
      </StageNote>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            基础信息
          </CardTitle>
        </CardHeader>
        <CardContent>
          <InfoGrid items={projectItems} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">生成参数</CardTitle>
        </CardHeader>
        <CardContent>
          <InfoGrid items={generationItems} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">项目标识</CardTitle>
        </CardHeader>
        <CardContent>
          <InfoGrid
            items={[
              { label: '项目 ID', value: project.id },
              { label: '工作区 ID', value: project.workspace_id },
            ]}
          />
          <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
            凭据只保存在服务端；本页面不会读取或展示任何供应商 API Key。
          </p>
        </CardContent>
      </Card>

      <Button variant="outline" size="sm" asChild>
        <a href={`/projects/${projectId}`} target="_blank" rel="noreferrer">
          打开旧版项目工作台
        </a>
      </Button>
    </div>
  )
}
