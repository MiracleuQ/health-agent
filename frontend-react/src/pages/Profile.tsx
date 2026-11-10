import { useEffect, useState } from 'react'
import { Card, Form, Input, Select, Button, Typography, message } from 'antd'
import api, { Profile as ProfileType } from '../services/api'

const { Item } = Form

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileType | null>(null)
  const [loading, setLoading] = useState(false)

  const loadProfile = async () => {
    try {
      const res = await api.get<{ code: number; data: ProfileType }>('/api/users/profile')
      if (res.code === 0) {
        setProfile(res.data)
      }
    } catch (err: any) {
      message.error('加载档案失败')
    }
  }

  useEffect(() => {
    loadProfile()
  }, [])

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      await api.post('/api/users/profile', values)
      message.success('档案已保存')
      loadProfile()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  if (!profile) {
    return (
      <Card style={{ padding: 40, textAlign: 'center' }}>
        <Typography.Text type="primary">暂无健康档案</Typography.Text>
      </Card>
    )
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Card title="我的健康档案" style={{ marginBottom: 24 }}>
        <Typography.Text>用户 ID：{profile.openid}</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>年龄：{profile.age ?? '-'}</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>性别：{profile.gender ?? '-'}</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>身高：{profile.height_cm ?? '-'} cm</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>体重：{profile.weight_kg ?? '-'} kg</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>活动水平：{profile.activity_level ?? '-'}</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>目标：{profile.goal ?? '-'}</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>目标卡路里：{profile.target_calories ?? '-'} 大卡</Typography.Text>
        <Typography.Text style={{ marginTop: 8 }}>训练周期：{profile.training_weeks ?? '-'} 周</Typography.Text>
      </Card>

      <Card title="更新档案">
        <Form
          layout="vertical"
          initialValues={profile}
          onFinish={handleSubmit}
        >
          <Item label="姓名" name="name"><Input /></Item>
          <Item label="年龄" name="age"><Input type="number" /></Item>
          <Item label="性别" name="gender">
            <Select options={['男', '女', '其他']} />
          </Item>
          <Item label="身高 (cm)" name="height_cm"><Input type="number" /></Item>
          <Item label="体重 (kg)" name="weight_kg"><Input type="number" /></Item>
          <Item label="活动水平" name="activity_level">
            <Select options={['sedentary', 'light', 'moderate', 'active', 'very_active']} />
          </Item>
          <Item label="目标" name="goal">
            <Select options={['fat_loss', 'muscle_gain', 'maintain']} />
          </Item>
          <Item label="目标卡路里" name="target_calories"><Input type="number" /></Item>
          <Item label="训练周期 (周)" name="training_weeks"><Input type="number" /></Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            保存档案
          </Button>
        </Form>
      </Card>
    </div>
  )
}