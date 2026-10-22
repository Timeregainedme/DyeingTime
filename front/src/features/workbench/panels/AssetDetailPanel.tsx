/**
 * 单个资产的详情面板。
 *
 * 只读展示后端真实字段；编辑、出图、候选确认仍走旧版资产编辑页。
 * 角色额外展示音色相关字段，因为它属于当前已生效的数据模型（P4 才做锁定）。
 */
import { ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import {
  WORKBENCH_ASSET_LABELS,
  workbenchAssetGroupPath,
  type WorkbenchAssetType,
} from '../routes'
import { useWorkbenchAssetDetail } from '../useWorkbenchQueries'
import { InfoGrid, type InfoItem } from '../components/InfoGrid'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import { legacyAssetEditPath } from './legacyPaths'

export function AssetDetailPanel({
  projectId,
  assetType,
  assetId,
  onNavigate,
}: {
  projectId: string
  assetType: WorkbenchAssetType
  assetId: string
  onNavigate: (path: string) => void
}) {
  const query = useWorkbenchAssetDetail(projectId, assetType, assetId)
  const label = WORKBENCH_ASSET_LABELS[assetType]

  if (query.isLoading) return <PanelLoading lines={6} label={`加载${label}详情`} />
  if (query.isError) {
    return (
      <PanelError
        message={query.error instanceof Error ? query.error.message : `${label}加载失败`}
        onRetry={() => void query.refetch()}
      />
    )
  }
  if (!query.data) {
    return (
      <PanelEmpty
        title={`没有找到该${label}`}
        description="资产可能已被删除，或不属于当前工作区。"
        action={
          <Button size="sm" onClick={() => onNavigate(workbenchAssetGroupPath(projectId, assetType))}>
            返回列表
          </Button>
        }
      />
    )
  }

  const data = query.data
  const items: InfoItem[] = [
    { label: '名称', value: String(data.name ?? '—') },
    { label: '题材', value: String(data.style ?? '—') },
    { label: '表现形式', value: String(data.visual_style ?? data.visualStyle ?? '—') },
    { label: '标签', value: Array.isArray(data.tags) && data.tags.length ? data.tags.join('、') : '—' },
    { label: '描述', value: String(data.description ?? '—') },
    { label: '资产 ID', value: assetId },
  ]

  if (assetType === 'character') {
    items.push(
      { label: '演员 ID', value: data.actor_id ? String(data.actor_id) : '未绑定' },
      { label: '服装 ID', value: data.costume_id ? String(data.costume_id) : '未绑定' },
      { label: '音色 ID', value: data.voice_id ? String(data.voice_id) : '未指定' },
      { label: '音色来源', value: data.voice_source ? String(data.voice_source) : '—' },
      { label: '音色描述', value: data.voice_description ? String(data.voice_description) : '—' },
    )
  }

  const thumbnail = typeof data.thumbnail === 'string' ? data.thumbnail : ''

  return (
    <div className="space-y-4">
      <PanelHeader
        title={String(data.name ?? '未命名资产')}
        description={`${label} · 只读详情`}
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate(workbenchAssetGroupPath(projectId, assetType))}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              返回列表
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw className={query.isFetching ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
              刷新
            </Button>
            <LegacyLink href={legacyAssetEditPath(projectId, assetType, assetId)}>
              <ExternalLink className="h-3.5 w-3.5" />
              旧版编辑
            </LegacyLink>
          </>
        }
      />

      <StageNote stage="P4">
        身份锁定、候选图确认与衍生版本将在 P4 完成。本阶段修改资产请使用旧版编辑页，改完回到此处刷新。
      </StageNote>

      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <Card>
          <CardContent className="p-3">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt={String(data.name ?? label)}
                className="max-h-64 w-full rounded-md bg-muted object-contain"
              />
            ) : (
              <div className="flex h-40 items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
                暂无图片
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <InfoGrid items={items} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
