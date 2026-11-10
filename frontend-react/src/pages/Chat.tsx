import { useState, useEffect, useRef } from 'react'
import { Input, Button, Card, Typography, Space, Divider, Tag } from 'antd'
import api from '../services/api'
import ChatBubble from '../components/ChatBubble'

const { Text } = Typography

export default function Chat() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastIntent, setLastIntent] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

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
      scrollToBottom()
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  return (
    <div style={{ height: 'calc(100vh - 120px)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <Card
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
        }}
        bodyStyle={{ overflowY: 'auto' }}
      >
        {messages.map((m, i) => (
          <ChatBubble key={i} text={m.content} isUser={m.role === 'user'} />
        ))}
        {loading && (
          <div style={{ marginBottom: 16, color: '#1890ff' }}>
            Agent 思考中 <span>···</span>
          </div>
        )}
        <div ref={endRef} />
      </Card>

      {lastIntent && (
        <div style={{ padding: '0 24px 8px', display: 'flex', gap: 8 }}>
          <Tag color="blue">意图：{lastIntent}</Tag>
        </div>
      )}

      <div style={{ padding: 16, borderTop: '1px solid #eee', background: '#fff' }}>
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: 8 }}>
          <Input
            placeholder="描述你的健康需求（例如：我想制定一个 8 周减脂计划，目标每日 1800 大卡）"
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
