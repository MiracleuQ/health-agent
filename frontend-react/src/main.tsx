import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import Antd from 'antd'
import 'antd/dist/reset.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Antd config={{ theme: { token: { colorPrimary: '#1890ff' } } }}>
      <App />
    </Antd>
  </React.StrictMode>,
)
