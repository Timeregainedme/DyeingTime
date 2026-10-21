import { AppstoreOutlined, DeleteOutlined, EditOutlined, FileTextOutlined } from '@ant-design/icons'
import { Button, Input, Space, Switch } from 'antd'

type ChapterStudioMaintenancePanelProps = {
  opsTitleDraft: string
  opsNoteDraft: string
  hideShot: boolean
  onChangeTitle: (value: string) => void
  onBlurTitle: () => void
  onChangeNote: (value: string) => void
  onBlurNote: () => void
  onToggleHidden: (value: boolean) => void
  onRequestDelete: () => void
}

export function ChapterStudioMaintenancePanel({
  opsTitleDraft,
  opsNoteDraft,
  hideShot,
  onChangeTitle,
  onBlurTitle,
  onChangeNote,
  onBlurNote,
  onToggleHidden,
  onRequestDelete,
}: ChapterStudioMaintenancePanelProps) {
  return (
    <div>
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-500">
        这里放的是次级维护动作，例如修改标题、补备注、隐藏或删除分镜。生成主线仍然建议优先使用“视频生成”“关键帧与参考图”“生成参数”这些模块。
      </div>

      <div className="cs-group">
        <div className="cs-group-title">
          <EditOutlined /> 基本维护
        </div>
        <div className="space-y-3">
          <div>
            <div className="text-gray-500 text-xs mb-1">分镜标题</div>
            <Input
              value={opsTitleDraft}
              placeholder="分镜标题…"
              onChange={(e) => onChangeTitle(e.target.value)}
              onBlur={onBlurTitle}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">隐藏此分镜</div>
              <div className="text-xs text-gray-500">隐藏后将不参与预览整章与导出</div>
            </div>
            <Switch checked={hideShot} onChange={onToggleHidden} />
          </div>
        </div>
      </div>

      <div className="cs-group">
        <div className="cs-group-title">
          <FileTextOutlined /> 维护备注
        </div>
        <Input.TextArea
          rows={3}
          value={opsNoteDraft}
          placeholder="备注…"
          onChange={(e) => onChangeNote(e.target.value)}
          onBlur={onBlurNote}
        />
      </div>

      <div className="cs-group">
        <div className="cs-group-title">
          <AppstoreOutlined /> 高风险操作
        </div>
        <div className="text-xs text-gray-500 mb-3">删除属于维护动作，不影响当前生成主线；如非必要，建议保留分镜并继续生成准备。</div>
        <Space wrap>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={onRequestDelete}
          >
            删除
          </Button>
        </Space>
      </div>
    </div>
  )
}
