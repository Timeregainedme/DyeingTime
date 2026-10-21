import { useNavigate, useParams } from 'react-router-dom'
import { PlaceholderTab } from './PlaceholderTab'
import { getProjectEditorPath } from '../routes'

export function EditTab() {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  return (
    <PlaceholderTab
      title="后期剪辑"
      description="时间线编辑器，或从可剪辑章节列表进入。"
      actionLabel="进入后期剪辑"
      onAction={() => projectId && navigate(getProjectEditorPath(projectId))}
    />
  )
}
