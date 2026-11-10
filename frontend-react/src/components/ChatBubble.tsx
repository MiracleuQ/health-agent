import { User, Robot, ClockCircle } from '@ant-design/icons'

type Props = {
  text: string
  isUser: boolean
}

export default function ChatBubble({ text, isUser }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        marginBottom: 16,
        maxWidth: '80%',
      }}
    >
      {isUser ? (
        <>
          <div style={{ marginRight: 8, fontSize: 18 }}>
            <User />
          </div>
          <div
            style={{
              background: '#e6f7ff',
              borderRadius: '8px 8px 0 8px',
              padding: 10,
              maxWidth: '60%',
            }}
          >
            {text}
          </div>
        </>
      ) : (
        <>
          <div style={{ marginRight: 8, fontSize: 18, color: '#52c41a' }}>
            <Robot />
          </div>
          <div
            style={{
              background: '#f6ffed',
              borderRadius: '8px 8px 8px 0',
              padding: 10,
              maxWidth: '70%',
              whiteSpace: 'pre-wrap',
            }}
          >
            {text}
          </div>
          <span
            style={{
              fontSize: 12,
              color: '#999',
              marginLeft: 8,
              marginTop: 4,
              display: 'inline-block',
            }}
          >
            <ClockCircle /> 刚刚
          </span>
        </>
      )}
    </div>
  )
}
