import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Card, Modal } from 'antd'

type DisplayImageCardProps = {
  title: ReactNode
  imageUrl?: string
  imageAlt: string
  placeholder?: ReactNode
  extra?: ReactNode
  actions?: ReactNode[]
  meta?: ReactNode
  footer?: ReactNode
  onImageClick?: () => void
  enablePreview?: boolean
  size?: 'small' | 'default'
  hoverable?: boolean
  imageHeightClassName?: string
}

export function DisplayImageCard({
  title,
  imageUrl,
  imageAlt,
  placeholder = '暂无图片',
  extra,
  actions,
  meta,
  footer,
  onImageClick,
  enablePreview = true,
  size = 'small',
  hoverable = true,
  imageHeightClassName = 'h-44',
}: DisplayImageCardProps) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const [imgError, setImgError] = useState(false)

  useEffect(() => {
    setImgError(false)
  }, [imageUrl])

  const handleImageClick = () => {
    if (onImageClick) {
      onImageClick()
      return
    }
    if (enablePreview && imageUrl) {
      setPreviewOpen(true)
    }
  }

  const displayUrl = imgError ? undefined : imageUrl

  return (
    <>
      <Card title={title} extra={extra} actions={actions} size={size} hoverable={hoverable}>
        <div
          className={`${imageHeightClassName} rounded-md border border-gray-200 bg-gray-50 flex items-center justify-center text-gray-500 text-sm overflow-hidden ${(onImageClick || (enablePreview && displayUrl)) ? 'cursor-pointer' : ''}`}
          onClick={handleImageClick}
        >
          {displayUrl ? (
            <img
              src={displayUrl}
              alt={imageAlt}
              className="w-full h-full object-contain p-1"
              onError={() => setImgError(true)}
            />
          ) : (
            placeholder
          )}
        </div>
        {meta ? <div className="mt-2">{meta}</div> : null}
        {footer ? <div className="mt-3">{footer}</div> : null}
      </Card>

      <Modal title={imageAlt} open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={960}>
        <div className="w-full flex justify-center bg-gray-50 rounded-md overflow-hidden">
          {displayUrl ? <img src={displayUrl} alt={imageAlt} className="max-h-[75vh] object-contain" /> : null}
        </div>
      </Modal>
    </>
  )
}

