import { useEffect, useState } from 'react'
import { Card, Table, Button, Typography, Space, Badge, message } from 'antd'
import api, { Plan as PlanType } from '../services/api'

const { Text } = Typography

export default function PlanPage() {
  const [plans, setPlans] = useState<PlanType[]>([])
  const [loading, setLoading] = useState(false)

  const loadPlans = async () => {
    setLoading(true)
    try {
      const res = await api.get<{ code: number; data: PlanType[] }>('/api/plans')
      if (res.code === 0) {
        setPlans(res.data)
      }
    } catch (err: any) {
      message.error('加载计划失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlans()
  }, [])

  const handleApprove = async (id: number, status: 'approved' | 'rejected') => {
    try {
      await api.post(`/api/plans/${id}/approve`, { status })
      message.success(status === 'approved' ? '计划已通过审核' : '计划已拒绝')
      loadPlans()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '审核失败')
    }
  }

  const columns = [
    {
      title: '计划 ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '计划类型',
      dataIndex: 'plan_type',
      key: 'plan_type',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (text: string) => {
        const color = text === 'approved' ? 'green' : text === 'rejected' ? 'red' : 'orange'
        return <Badge status={text} text={text} color={color} />
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (text: any, record: PlanType) => {
        if (record.status === 'pending') {
          return (
            <Space>
              <Button type="primary" size="small" onClick={() => handleApprove(record.id, 'approved')}>
                审核通过
              </Button>
              <Button size="small" onClick={() => handleApprove(record.id, 'rejected')}>
                拒绝
              </Button>
            </Space>
          )
        }
        return <Text>{record.status}</Text>
      },
    },
  ]

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Card title="我的健康计划" extra={<Button onClick={loadPlans}>刷新</Button>} style={{ marginBottom: 24 }}>
        <Text type="secondary">
          健康计划生成后默认进入 pending 状态，需要专业审核通过后才正式生效。
        </Text>
      </Card>

      <Table
        dataSource={plans}
        columns={columns}
        rowKey="id"
        loading={loading}
        locale={{
          emptyText: '暂无计划，先在对话中制定一个吧。',
        }}
      />
    </div>
  )
}