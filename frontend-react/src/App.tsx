import { useState } from 'react'
import { Button, Card, Input, message, Space, Typography, Divider, Tag } from 'antd'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, Link } from 'react-router-dom'
import { LogoutOutlined, UserOutlined, CommentOutlined, CalendarOutlined, UserIconOutlined, DashboardOutlined } from '@ant-design/icons'
import api from './services/api'
import ChatBubble from './components/ChatBubble'

const { Text } = Typography

// ---------- 登录页 ----------
function LoginPage() {
  const [openid, setOpenid] = useState('demo_user')

  const handleLogin = async () => {
    try {
      const res: any = await api.post('/api/v1/auth/login', { openid })
      localStorage.setItem('token', res.access_token)
      message.success(`欢迎，${res.openid}`)
      window.location.reload()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '登录失败')
    }
  }

  return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Card style={{ width: 380, padding: 40 }} title="AI 健康管理登录">
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
          演示版：任意输入 OpenID 即可登录
        </p>
      </Card>
    </div>
  )
}

// ---------- AI 对话页 ----------
function ChatPage() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastIntent, setLastIntent] = useState<string | null>(null)

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    const userMsg = input
    setInput('')
    setLoading(true)
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])

    try {
      const res = await api.post('/api/chat', { message: userMsg })
      const assistantMsg = res.reply || '未收到回复'
      setMessages((prev) => [...prev, { role: 'assistant', content: assistantMsg }])
      setLastIntent(res.intent || null)
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `❌ 请求失败：${err.response?.data?.detail || err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ padding: 16, borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff' }}>💬 AI 健康对话</span>
        <div>
          {lastIntent && <Tag color="blue">意图：{lastIntent}</Tag>}
          <Button onClick={() => { localStorage.removeItem('token'); window.location.reload() }} style={{ marginLeft: 12 }}>
            <LogoutOutlined /> 退出
          </Button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {messages.map((m, i) => (
          <ChatBubble key={i} text={m.content} isUser={m.role === 'user'} />
        ))}
        {loading && <div style={{ marginBottom: 16, color: '#1890ff' }}>Agent 思考中···</div>}
      </div>

      <div style={{ padding: 16, borderTop: '1px solid #eee', background: '#fff' }}>
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 8 }}>
          <Input
            placeholder="例如：我想制定一个 8 周减脂计划，目标每日 1800 大卡"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={sendMessage}
            style={{ flex: 1 }}
          />
          <Button type="primary" disabled={loading} htmlType="submit">
            发送
          </Button>
        </form>
        <Divider orientation="left">快捷示例</Divider>
        <Space wrap style={{ marginTop: 8 }}>
          <Button size="small" onClick={() => setInput('我想制定一个 8 周减脂计划，目标每日 1800 大卡')}>
            制定减脂计划
          </Button>
          <Button size="small" onClick={() => setInput('中午吃了鸡胸肉沙拉，配一碗糙米饭，估算卡路里')}>
            食物卡路里估算
          </Button>
          <Button size="small" onClick={() => setInput('记录今天：体重 70kg，摄入 1700 大卡，运动 40 分钟')}>
            每日打卡
          </Button>
          <Button size="small" onClick={() => setInput('减脂期间怎么吃主食？')}>
            营养咨询
          </Button>
        </Space>
      </div>
    </div>
  )
}

// ---------- 其他页面（占位，避免路由报错） ----------
function PagePlaceholder(title: string) {
  return (
    <div style={{ padding: 24, minHeight: 'calc(100vh - 56px)' }}>
      <h2 style={{ color: '#1890ff' }}>{title}</h2>
      <p>该页面功能正在完善中，请先体验 AI 对话功能。</p>
    </div>
  )
}

const ProfilePage = () => <PagePlaceholder>个人档案</PagePlaceholder>
const PlanPage = () => <PagePlaceholder>健康计划</PagePlaceholder>
const DashboardPage = () => <PagePlaceholder>数据看板</PagePlaceholder>

// ---------- 主应用 ----------
export default function App() {
  const token = localStorage.getItem('token')
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  if (!token) {
    return <LoginPage />
  }

  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
        {/* 左侧导航 */}
        <div style={{ width: 200, background: '#fafafa', borderRight: '1px solid #eee', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: 20, fontSize: 18, fontWeight: 'bold', color: '#1890ff', borderBottom: '1px solid #eee' }}>
            健康管理 Agent
          </div>
          <div style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: '#333' }}
            onClick={() => navigate('/chat')}>
            <CommentOutlined /> 对话
          </div>
          <div style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: '#333' }}
            onClick={() => navigate('/profile')}>
            <UserIconOutlined /> 档案
          </div>
          <div style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: '#333' }}
            onClick={() => navigate('/plan')}>
            <CalendarOutlined /> 计划
          </div>
          <div style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: '#333' }}
            onClick={() => navigate('/dashboard')}>
            <DashboardOutlined /> 看板
          </div>
          <div style={{ marginTop: 'auto', padding: 20, color: '#999', fontSize: 12, borderTop: '1px solid #eee' }}>
            <LogoutOutlined onClick={handleLogout} style={{ cursor: 'pointer', marginRight: 8 }} />
            退出登录
          </div>
        </div>

        {/* 右侧内容 */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/plan" element={<PlanPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/" element={<Navigate to="/chat" replace />} />
          </Routes>
        </div>
      </div>
    </Router>
  )
}