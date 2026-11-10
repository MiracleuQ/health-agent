import { useState } from 'react'
import { Button, Card, Input, message } from 'antd'
import { LoginOutlined, UserOutlined } from '@ant-design/icons'
import api, { LoginResponse } from '../services/api'

export default function Login() {
  const [openid, setOpenid] = useState('demo_user')

  const handleLogin = async () => {
    try {
      const res: LoginResponse = await api.post('/api/v1/auth/login', { openid })
      localStorage.setItem('token', res.access_token)
      message.success(`欢迎，${res.openid}`)
      window.location.href = '/'
    } catch (err: any) {
      message.error(err.response?.data?.detail || '登录失败')
    }
  }

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f0f2f5',
      }}
    >
      <Card
        style={{ width: 380, padding: 40 }}
        title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><LoginOutlined /> AI 健康管理登录</span>}
        extra={<a>没有账号？立即注册</a>}
      >
        <div style={{ marginBottom: 24 }}>
          <UserOutlined style={{ fontSize: 16, color: '#999', marginRight: 8 }} />
          <Input
            placeholder="请输入用户标识（OpenID）"
            value={openid}
            onChange={(e) => setOpenid(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <Button type="primary" onClick={handleLogin} style={{ width: '100%' }}>
          登录
        </Button>
        <p style={{ marginTop: 16, fontSize: 12, color: '#999', textAlign: 'center' }}>
          演示版：任意输入 OpenID 即可登录，系统将自动生成 JWT 凭据
        </p>
      </Card>
    </div>
  )
}
