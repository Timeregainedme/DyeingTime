import { AssetTypeTab } from './AssetTypeTab'
import { useNavigate } from 'react-router-dom'
import { StudioEntitiesApi } from '../../../../services/studioEntities'

export function PropsTab() {
  const navigate = useNavigate()

  return (
    <AssetTypeTab
      label="道具"
      tabKey="prop"
      listAssets={async ({ q, page, pageSize }) => {
        const res = await StudioEntitiesApi.list('prop', { q: q ?? null, page, pageSize })
        return { items: (res.data?.items ?? []) as any[], total: res.data?.pagination.total ?? 0 }
      }}
      createAsset={async (payload) => {
        const res = await StudioEntitiesApi.create('prop', payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty prop')
        return res.data as any
      }}
      updateAsset={async (id, payload) => {
        const res = await StudioEntitiesApi.update('prop', id, payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty prop')
        return res.data as any
      }}
      deleteAsset={async (id) => {
        await StudioEntitiesApi.remove('prop', id)
      }}
      onEditAsset={(asset) => {
        navigate(`/assets/props/${asset.id}/edit`)
      }}
    />
  )
}
