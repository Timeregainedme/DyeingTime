import { AssetTypeTab } from './AssetTypeTab'
import { useNavigate } from 'react-router-dom'
import { StudioEntitiesApi } from '../../../../services/studioEntities'

export function CostumesTab() {
  const navigate = useNavigate()

  return (
    <AssetTypeTab
      label="服装"
      tabKey="costume"
      listAssets={async ({ q, page, pageSize }) => {
        const res = await StudioEntitiesApi.list('costume', { q: q ?? null, page, pageSize })
        return { items: (res.data?.items ?? []) as any[], total: res.data?.pagination.total ?? 0 }
      }}
      createAsset={async (payload) => {
        const res = await StudioEntitiesApi.create('costume', payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty costume')
        return res.data as any
      }}
      updateAsset={async (id, payload) => {
        const res = await StudioEntitiesApi.update('costume', id, payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty costume')
        return res.data as any
      }}
      deleteAsset={async (id) => {
        await StudioEntitiesApi.remove('costume', id)
      }}
      onEditAsset={(asset) => {
        navigate(`/assets/costumes/${asset.id}/edit`)
      }}
    />
  )
}
