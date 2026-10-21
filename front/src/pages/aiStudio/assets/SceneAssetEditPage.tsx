import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { AssetEditPageBase } from './components/AssetEditPageBase'
import { assetAdapters } from './assetAdapters'
import { decodeAssetEditReturnTo } from '../project/ProjectWorkbench/utils/workbenchAssetReturnTo'

export default function SceneAssetEditPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { sceneId } = useParams<{ sceneId: string }>()
  const adapter = assetAdapters.scene
  const backTo = decodeAssetEditReturnTo(searchParams.get('returnTo'), adapter.backTo)

  return (
    <AssetEditPageBase<any, any>
      assetId={sceneId}
      onNavigate={(to, replace) => navigate(to, replace ? { replace: true } : undefined)}
      {...adapter}
      backTo={backTo}
    />
  )
}

