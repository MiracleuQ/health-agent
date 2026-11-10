# 🏥 AI 健康管理 Agent（生产级大模型应用）

基于 **LangGraph + FastAPI + React** 的企业级健康管理多代理 Agent，支持个性化减脂/增肌计划、多模态食物卡路里估算、一周膳食计划与购物清单、饮食偏好管理、PDF 健康报告导出、每日打卡与进度可视化，并内置**数据中台**与**评测中台**。

## 🏗️ 整体架构（生产级）

```
┌─────────────────────────────────────────────────────────────┐
│                    React + Ant Design 前端 (SPA)              │
│  登录 | AI 对话 | 档案 | 健康计划 | 食物估算 | 数据看板 | 评测看板 │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP/REST (JWT)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                      │
│  /api/v1/auth | /api/v1/users | /api/v1/plans | /api/v1/chat   │
│  /api/v1/data/*   (数据中台)    /api/v1/eval/* (评测中台)        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌────────────────┐    ┌──────────────┐
│  数据中台     │    │  评测中台      │    │  Agent 业务层 │
│ (Data Platform)│   │(Eval Platform) │    │(LangGraph)   │
│ - 埋点采集    │    │ - 数据集管理   │    │ - 意图路由   │
│ - 脱敏治理   │    │ - 离线评测引擎 │    │ - 工具调用   │
│ - 数据服务API│    │ - 指标计算报告 │    │ - 记忆检索   │
└──────────────┘    └────────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                        ┌─────▼─────┐
                        │  SQLite / │
                        │ ChromaDB  │
                        └───────────┘
```

## 📁 项目结构

```
health_agent_project/
├── run.py                    # 统一入口: api / web / cli
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板（含 JWT 密钥）
├── pyproject.toml            # pytest 配置
├── Dockerfile.prod           # 后端生产镜像
├── docker-compose.prod.yml   # 后端 + 前端 一键部署
├── README.md
│
├── app/                      # FastAPI 后端
│   ├── main.py               # 应用入口 + 路由注册 + 启动初始化
│   ├── core/
│   │   ├── config.py         # Pydantic Settings 统一配置（含 JWT）
│   │   └── logging.py        # Loguru 结构化日志
│   ├── db/
│   │   └── database.py       # SQLite 持久化层（用户/计划/记录/偏好/膳食）
│   ├── agents/               # LangGraph 多代理
│   │   ├── state.py          # 共享状态
│   │   ├── memory.py         # SQLite Checkpoint 持久化（多轮记忆）
│   │   ├── nodes.py          # 9 个代理节点（含人工审批）
│   │   └── graph.py          # 图编排与编译
│   ├── tools/                # health_tools.py（20 个 Function Calling 工具）
│   ├── services/             # knowledge.py（Chroma RAG 知识库）
│   ├── dataplatform/         # 🆕 数据中台
│   │   ├── collector.py      # 埋点采集器（自动记录事件）
│   │   ├── models.py         # 中台数据模型与建表
│   │   ├── service.py        # 数据服务（查询、聚合、脱敏、看板）
│   │   └── router.py         # /api/v1/data/* 路由
│   ├── evalplatform/         # 🆕 评测中台
│   │   ├── datasets.py       # 评测数据集管理
│   │   ├── runner.py         # 离线评测引擎
│   │   ├── metrics.py        # 指标计算
│   │   ├── judge.py          # LLM-as-judge 打分
│   │   ├── report.py         # HTML 评测报告生成
│   │   └── router.py         # /api/v1/eval/* 路由
│   ├── api/                  # RESTful 接口
│   │   ├── auth.py           # JWT 登录 /me
│   │   ├── chat.py           # Agent 对话（接入埋点）
│   │   ├── users.py          # 用户档案（JWT + 埋点）
│   │   ├── plans.py          # 计划管理 + 人工审核（JWT + 埋点）
│   │   ├── records.py        # 打卡记录 + 图表数据（JWT + 埋点）
│   │   ├── reports.py        # PDF 报告下载（JWT）
│   │   └── deps.py           # JWT 依赖注入
│   └── cli.py                # 命令行交互入口
│
├── frontend-react/           # 🆕 React 生产级前端（替代 Streamlit）
│   ├── Dockerfile            # 前端生产镜像（Nginx）
│   ├── nginx.conf            # 前端静态 + API 代理
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx           # 路由 + 侧边栏 + JWT 登录拦截
│       ├── services/api.ts   # Axios 封装（自动注入 Token）
│       ├── components/
│       │   ├── ProtectedRoute.tsx  # 权限守卫
│       │   └── ChatBubble.tsx      # 对话气泡
│       └── pages/
│           ├── Login.tsx     # 登录页
│           ├── Chat.tsx      # AI 对话页（核心）
│           ├── Profile.tsx   # 健康档案页
│           ├── Plan.tsx      # 健康计划页（含人工审核）
│           └── Dashboard.tsx # 数据看板页
│
├── tests/                    # 单元测试
│   ├── test_tools.py
│   └── test_graph.py
│
├── .gitignore                # 保护 .env、node_modules、*.db 等
└── reports/                  # PDF 健康报告输出目录
```

## 🚀 快速开始

### 1. 克隆与配置

```bash
cd health_agent_project

# 推荐使用 Python 虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量（已包含你的 API Key）
copy .env.example .env          # Windows
# cp .env.example .env          # Mac/Linux
```

### 2. 启动后端 API

```bash
python run.py api
# 访问 http://localhost:8000/docs 查看 Swagger 接口文档
```

### 3. 启动前端 Web（推荐面试演示）

```bash
cd frontend-react
npm install
npm run dev
# 访问 http://localhost:3000
```

### 4. Docker 生产部署（一键）

```bash
docker-compose -f docker-compose.prod.yml up -d
# 前端：http://localhost:80
# 后端 API：http://localhost:8000/docs
```

### 5. 命令行对话

```bash
python run.py cli
```

### 6. 运行评测（验证 Agent 质量）

```bash
# 启动后端后，调用评测接口
curl -X POST http://localhost:8000/api/v1/eval/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'

# 查看评测报告
curl http://localhost:8000/api/v1/eval/report/<run_id>
```

### 7. 运行单元测试

```bash
pytest
```

## 💡 核心功能

| 模块 | 功能 | 技术实现 |
|------|------|---------|
| **多代理编排** | 协调器路由 → 计划/营养/运动/打卡/知识/食物估算/膳食计划/饮食偏好/报告 9 个专业代理 | LangGraph StateGraph |
| **个性化计划** | 基于目标卡路里、训练周期生成减脂/增肌/维持计划 | Function Calling + 工具计算 |
| **人工审核 (HITL)** | 计划默认 `pending`，需专业审核通过后生效 | LangGraph 节点 + FastAPI 接口 |
| **多轮对话记忆** | 基于 SQLite Checkpoint 的断点续对与会话隔离 | `langgraph-checkpoint-sqlite` |
| **多模态食物估算** | 输入食物描述，AI 估算卡路里/营养并自动写入打卡 | Function Calling + 营养数据库 |
| **一周膳食计划** | 7 天三餐建议 + 去重购物清单，尊重过敏原/忌口/素食/清真约束 | 结构化 JSON 生成 |
| **饮食偏好管理** | 过敏原、忌口、菜系、素食/清真设置，代理层硬约束 | SQLite 持久化 |
| **PDF 健康报告** | 生成周报/月报 PDF，含打卡记录、膳食计划、购物清单 | ReportLab + FastAPI 文件下载 |
| **每日打卡** | 体重/卡路里/运动/饮水记录，近 30 天趋势图表 | SQLite + Plotly |
| **RESTful API** | 完整后端接口，支持前后端分离 | FastAPI + Swagger (/docs) |
| **JWT 鉴权** | Bearer Token 鉴权，兼容 X-OpenID 演示模式 | python-jose + passlib |
| **数据中台** | 埋点采集、PII 脱敏、数据治理、标准化查询/导出 | SQLite + 埋点装饰器 |
| **评测中台** | 离线评测引擎、意图/工具/安全指标、HTML 报告 | LLM-as-judge + 批量运行 |
| **可观测性** | LLM 调用链追踪与调试 | LangSmith (可选) |
| **工程素养** | Pydantic Settings、Loguru 日志、pytest 单元测试、Docker | 生产级代码结构 |

## 🎯 为什么适合“大模型应用工程师”岗位

1. **主流框架实战**：LangGraph + LangChain，多代理编排，非简单 Prompt 堆砌。
2. **Function Calling 工程化**：20 个工具覆盖计算、数据、文件生成，逻辑严谨不幻觉。
3. **多模态能力**：食物卡路里估算，展示大模型多模态应用潜力。
4. **人工干预 (HITL)**：健康计划涉及身体安全，加入 `pending` 审核节点。
5. **结构化生成**：膳食计划输出结构化 JSON + 购物清单，可直接落地执行。
6. **前后端分离**：React + Ant Design SPA，FastAPI 后端，Docker 容器化部署。
7. **数据中台**：埋点采集、脱敏治理、统一数据服务，体现数据工程能力。
8. **评测中台**：离线评测引擎、LLM-as-judge、HTML 报告，体现 LLM 应用质量保障能力。
9. **可观测性**：预留 LangSmith 接入点，便于生产调试。
10. **测试与配置**：Pydantic Settings、Loguru、pytest 单元测试，符合企业规范。

## 🔒 安全提醒

- `.env` 包含敏感密钥，**已在 `.gitignore` 中排除，请勿提交到 Git**。
- 生产环境请修改 `SECRET_KEY`，并接入真实用户认证系统。
- 健康建议仅供参考，不替代专业医疗诊断。

## 📄 许可

MIT License
