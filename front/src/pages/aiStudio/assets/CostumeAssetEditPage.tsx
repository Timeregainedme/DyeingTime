import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { AssetEditPageBase } from './components/AssetEditPageBase'
import { assetAdapters } from './assetAdapters'
import { decodeAssetEditReturnTo } from '../project/ProjectWorkbench/utils/workbenchAssetReturnTo'

export default function CostumeAssetEditPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { costumeId } = useParams<{ costumeId: string }>()
  const adapter = assetAdapters.costume
  const backTo = decodeAssetEditReturnTo(searchParams.get('returnTo'), adapter.backTo)

  return (
    <AssetEditPageBase<any, any>
      assetId={costumeId}
      onNavigate={(to, replace) => navigate(to, replace ? { replace: true } : undefined)}
      {...adapter}
      backTo={backTo}
    />
  )
}

