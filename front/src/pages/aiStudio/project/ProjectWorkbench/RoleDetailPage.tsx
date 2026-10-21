import { useNavigate, useParams } from 'react-router-dom'
import { AssetEditPageBase } from '../../assets/components/AssetEditPageBase'
import { assetAdapters } from '../../assets/assetAdapters'

export default function RoleDetailPage() {
  const navigate = useNavigate()
  const { projectId, characterId } = useParams<{ projectId: string; characterId: string }>()
  const adapter = assetAdapters.character

  if (!characterId) {
    return null
  }

  return (
    <AssetEditPageBase<any, any>
      assetId={characterId}
      {...adapter}
      backTo={projectId ? `/projects/${projectId}?tab=roles` : adapter.backTo}
      onNavigate={(to, replace) => navigate(to, replace ? { replace: true } : undefined)}
    />
  )
}
