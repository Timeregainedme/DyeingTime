/**
 * 风格圣经面板。
 *
 * 当前系统只有「项目题材 + 表现形式 + 风格目录（project_styles）」，
 * 没有风格参考图、测试样张与锁定快照——这些属于 P2。
 * 本面板只展示真实存在的字段与目录，避免把「名字叫风格圣经」当成已完成的风格系统。
 */
import { ExternalLink, Palette } from 'lucide-react'
import type { ProjectRead } from '../../../services/generated'
import { Badge } from '../../../components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { cn } from '../../../lib/utils'
import { InfoGrid } from '../components/InfoGrid'
import { LegacyLink, PanelHeader } from '../components/PanelHeader'
import { PanelLoading, StageNote } from '../components/PanelStates'
import { useWorkbenchStyleCatalog, useWorkbenchStyleOptions } from '../useWorkbenchQueries'

export function StylePanel({
  project,
}: {
  projectId: string
  project?: ProjectRead
}) {
  const catalogQuery = useWorkbenchStyleCatalog()
  const optionsQuery = useWorkbenchStyleOptions()

  if (catalogQuery.isLoading || optionsQuery.isLoading) {
    return <PanelLoading lines={6} label="加载风格目录" />
  }

  const catalog = catalogQuery.data ?? []
  const visualStyles = optionsQuery.data?.visual_styles ?? []

  /** 目录的 visual_style 是字符串值；用选项接口把它映射成可读名称。 */
  const visualLabel = (value: string) =>
    visualStyles.find((option) => option.value === value)?.label ?? value

  const groups = new Map<string, typeof catalog>()
  catalog.forEach((style) => {
    const list = groups.get(style.visual_style) ?? []
    list.push(style)
    groups.set(style.visual_style, list)
  })

  return (
    <div className="space-y-4">
      <PanelHeader
        title="风格圣经"
        description="当前项目的题材与画面表现形式，以及工作区可用的风格目录。"
        actions={
          <LegacyLink href="/styles">
            <ExternalLink className="h-3.5 w-3.5" />
            管理风格目录
          </LegacyLink>
        }
      />

      <StageNote stage="P2">
        1–3 张风格参考图分析、测试样张确认、风格锁定快照与「锁定后不可直接切换」将在 P2
        落地。当前风格目录只提供名称、说明与提示词质感描述。
      </StageNote>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Palette className="h-4 w-4 text-muted-foreground" />
            当前项目风格
          </CardTitle>
        </CardHeader>
        <CardContent>
          <InfoGrid
            items={[
              { label: '题材 / 风格', value: project?.style ?? '—' },
              { label: '表现形式', value: project?.visual_style ?? '—' },
              { label: '统一风格', value: project?.unify_style ? '是' : '否' },
              { label: '锁定状态', value: '未锁定（P2 提供）' },
            ]}
          />
        </CardContent>
      </Card>

      {catalogQuery.isError ? (
        <Card>
          <CardContent className="p-4 text-xs text-destructive">
            风格目录加载失败：
            {catalogQuery.error instanceof Error ? catalogQuery.error.message : '未知错误'}
          </CardContent>
        </Card>
      ) : null}

      {catalog.length === 0 ? (
        <Card>
          <CardContent className="p-4 text-xs text-muted-foreground">
            风格目录为空。可以在「管理风格目录」中新增，首次访问时后端会用内置枚举做种子。
          </CardContent>
        </Card>
      ) : (
        Array.from(groups.entries()).map(([visualStyle, styles]) => (
          <Card key={visualStyle}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{visualLabel(visualStyle)}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-2 2xl:grid-cols-3">
                {styles.map((style) => {
                  const active = project?.style === style.name
                  return (
                    <div
                      key={style.id}
                      className={cn(
                        'rounded-md border p-3 text-xs',
                        active ? 'border-primary/60 bg-primary/5' : 'border-border',
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{style.name}</span>
                        {active ? <Badge variant="secondary">当前项目</Badge> : null}
                      </div>
                      <p className="mt-1 leading-5 text-muted-foreground">
                        {style.description || '暂无说明'}
                      </p>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ))
      )}

      <p className="text-[10px] leading-4 text-muted-foreground">
        风格参考图默认不会加入 H3 镜头的参考图列表；它只服务于统一风格提示词与资产生成策略。
      </p>
    </div>
  )
}
