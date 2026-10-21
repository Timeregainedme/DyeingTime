import { AssetTypeTab } from './AssetTypeTab'
import { useNavigate } from 'react-router-dom'
import { StudioEntitiesApi } from '../../../../services/studioEntities'

export function ScenesTab() {
  const navigate = useNavigate()

  return (
    <AssetTypeTab
      label="场景"
      tabKey="scene"
      listAssets={async ({ q, page, pageSize }) => {
        const res = await StudioEntitiesApi.list('scene', { q: q ?? null, page, pageSize })
        return { items: (res.data?.items ?? []) as any[], total: res.data?.pagination.total ?? 0 }
      }}
      createAsset={async (payload) => {
        const res = await StudioEntitiesApi.create('scene', payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty scene')
        return res.data as any
      }}
      updateAsset={async (id, payload) => {
        const res = await StudioEntitiesApi.update('scene', id, payload as Record<string, unknown>)
        if (!res.data) throw new Error('empty scene')
        return res.data as any
      }}
      deleteAsset={async (id) => {
        await StudioEntitiesApi.remove('scene', id)
      }}
      onEditAsset={(asset) => {
        navigate(`/assets/scenes/${asset.id}/edit`)
      }}
    />
  )
}
