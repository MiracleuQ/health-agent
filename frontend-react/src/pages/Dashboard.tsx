import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Space, Button } from 'antd'
import api, { DashboardMetrics } from '../services/api'

const { Title, Text } = Typography

export default function Dashboard() {
  const [data, setData] = useState<DashboardMetrics | null>(null)

  const loadDashboard = async () => {
    try {
      const res = await api.get<{ code: number; data: DashboardMetrics }>('/api/v1/data/dashboard?days=7')
      if (res.code === 0) {
        setData(res.data)
      }
    } catch (err: any) {
      // 静默失败，看板为可选功能
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const card = (title: string, value: number | string, sub: string) => (
    <Card
      style={{ minWidth: 200 }}
      title={title}
      extra={sub}
      style2={{ marginBottom: 16 }}
    >
      <Title level={3} style={{ color: '#1890ff', margin: 0 }}>
        {value}
      </Title>
    </Card>
  )

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Row gutter={16}>
        <Col span={6}>
          {card('本周对话次数', data?.metrics.total_chats ?? '-', '与 AI 的交互轮次')}
        </Col>
        <Col span={6}>
          {card('计划生成数', data?.metrics.total_plans ?? '-', '健康计划条目')}
        </Col>
        <Col span={6}>
          {card('打卡记录数', data?.metrics.total_records ?? '-', '每日健康打卡')}
        </Col>
        <Col span={6}>
          {card('工具调用成功率', `${(data?.metrics.tool_success_rate ?? 0) * 100}%`, 'Function Calling 可靠性')}
        </Col>
      </Row>

      {data && (
        <Card title="每日活跃趋势" style={{ marginTop: 24 }}>
          <div style={{ height: 300 }}>
            {/* 简易折线，若需图表可接入 Ant Design Charts */}
            <ul style={{ padding: 0, margin: 0, listStyle: 'none', display: 'flex', gap: 12, height: '100%', alignItems: 'flex-end' }}>
              {data.daily_trend.map((d) => (
                <li
                  key={d.day}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column-reverse',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <div
                    style={{
                      width: 24,
                      height: `${(d.cnt / Math.max(...data.daily_trend.map((x) => x.cnt), 1)) * 100}%`,
                      background: '#1890ff',
                      borderRadius: '4px 4px 0 0',
                    }}
                  />
                  <span style={{ fontSize: 12, color: '#999' }}>{d.day}</span>
                  <span style={{ fontSize: 12 }}>{d.cnt}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      )}
    </div>
  )
}
