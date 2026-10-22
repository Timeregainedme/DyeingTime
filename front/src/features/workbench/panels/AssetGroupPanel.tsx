/**
 * 资产列表面板（角色 / 场景 / 道具 / 服装）。
 *
 * 数据来源：
 *   - 角色：项目内实体（实体接口按工作区返回后按 project_id 收敛）；
 *   - 场景 / 道具 / 服装：工作区级全局资产。
 *
 * P1 的边界：列表可搜索、可进入详情、可跳旧版编辑；
 * 候选图、身份锁定、衍生版本属于 P4，不在这里伪造按钮。
 */
import { useDeferredValue, useMemo, useState } from 'react'
import { ExternalLink, Search, X } from 'lucide-react'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import { Input } from '../../../components/ui/input'
import { cn } from '../../../lib/utils'
import {
  WORKBENCH_ASSET_LABELS,
  workbenchAssetDetailPath,
  type WorkbenchAssetType,
} from '../routes'
import type { WorkbenchAssetItem } from '../types'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelEmpty, PanelError, PanelLoading, StageNote } from '../components/PanelStates'
import { legacyAssetEditPath, legacyAssetListPath } from './legacyPaths'

function AssetThumb({ src, alt }: { src?: string; alt: string }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return (
      <div className="flex h-24 items-center justify-center rounded-md bg-muted text-[11px] text-muted-foreground">
        暂无图片
      </div>
    )
  }
  return (
    <div className="h-24 overflow-hidden rounded-md bg-muted">
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className="h-full w-full object-cover"
        onError={() => setFailed(true)}
      />
    </div>
  )
}

export function AssetGroupPanel({
  projectId,
  assetType,
  assets,
  loading,
  error,
  onRetry,
  onNavigate,
}: {
  projectId: string
  assetType: WorkbenchAssetType
  assets: WorkbenchAssetItem[]
  loading: boolean
  error: unknown
  onRetry: () => void
  onNavigate: (path: string) => void
}) {
  const [keyword, setKeyword] = useState('')
  const deferredKeyword = useDeferredValue(keyword)

  const visible = useMemo(() => {
    const normalized = deferredKeyword.trim().toLowerCase()
    if (!normalized) return assets
    return assets.filter(
      (asset) =>
        asset.name.toLowerCase().includes(normalized) ||
        (asset.description ?? '').toLowerCase().includes(normalized),
    )
  }, [assets, deferredKeyword])

  const label = WORKBENCH_ASSET_LABELS[assetType]

  if (loading) return <PanelLoading lines={5} label={`加载${label}`} />
  if (error) {
    return (
      <PanelError
        message={error instanceof Error ? error.message : `${label}加载失败`}
        onRetry={onRetry}
      />
    )
  }

  return (
    <div className="space-y-4">
      <PanelHeader
        title={`全局资产 · ${label}`}
        description={
          assetType === 'character'
            ? '当前项目的角色。角色是项目内资产，跨项目不共用。'
            : '工作区级全局资产，可在同一项目的不同剧集中复用。'
        }
        actions={
          <LegacyLink href={legacyAssetListPath(projectId, assetType)}>
            <ExternalLink className="h-3.5 w-3.5" />
            旧版资产管理
          </LegacyLink>
        }
      />

      <StageNote stage="P4">
        点击资产进入角色圣经 / 版本编辑：可维护别名、基础图候选、视觉身份锁定、造型衍生、音色与版本历史。
      </StageNote>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder={`搜索${label}名称或描述`}
          className="h-8 pl-8 pr-8 text-xs"
        />
        {keyword ? (
          <button
            type="button"
            aria-label="清空搜索"
            className="absolute right-1.5 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-muted-foreground hover:bg-accent"
            onClick={() => setKeyword('')}
          >
            <X className="h-3 w-3" />
          </button>
        ) : null}
      </div>

      {assets.length === 0 ? (
        <PanelEmpty
          title={`还没有${label}`}
          description={
            assetType === 'character'
              ? '角色通常由剧本提取或一键创建资产产生；进入详情可补基础形象并锁定身份。'
              : '全局资产在旧版资产管理页创建；进入详情可补基础版本与衍生版本。'
          }
          action={
            <LegacyLink href={legacyAssetListPath(projectId, assetType)}>
              去旧版创建{label}
            </LegacyLink>
          }
        />
      ) : visible.length === 0 ? (
        <PanelEmpty title="没有匹配的资产" description="清空搜索词后恢复完整列表。" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {visible.map((asset) => (
            <Card key={asset.id} className="overflow-hidden">
              <CardContent className="space-y-2 p-3">
                <AssetThumb src={asset.thumbnail} alt={asset.name} />
                <button
                  type="button"
                  className={cn(
                    'block w-full truncate text-left text-sm font-medium',
                    'hover:text-primary',
                  )}
                  onClick={() =>
                    onNavigate(workbenchAssetDetailPath(projectId, assetType, asset.id))
                  }
                >
                  {asset.name}
                </button>
                <p className="line-clamp-2 min-h-[2rem] text-[11px] leading-4 text-muted-foreground">
                  {asset.description || '暂无描述'}
                </p>
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-[10px] text-muted-foreground">
                    {asset.style || '未设定风格'}
                  </span>
                  <Button variant="ghost" size="sm" className="h-6 px-1.5 text-[11px]" asChild>
                    <a
                      href={legacyAssetEditPath(projectId, assetType, asset.id)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      旧版编辑
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
