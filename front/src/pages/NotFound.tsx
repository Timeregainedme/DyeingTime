import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const NotFound: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation('notFound')

  return (
    <Result
      status="404"
      title="404"
      subTitle={t('subTitle')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('backHome')}
        </Button>
      }
    />
  )
}

export default NotFound

