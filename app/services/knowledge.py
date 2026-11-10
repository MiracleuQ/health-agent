"""健康管理知识库（RAG）：基于 Chroma + OpenAI Embeddings。"""
from typing import List
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

try:
    from app.core.config import settings as _settings
    PERSIST_DIR = _settings.CHROMA_PERSIST_DIR
except Exception:  # pragma: no cover
    PERSIST_DIR = "./chroma_db"

HEALTH_KNOWLEDGE: List[str] = [
    "减脂的核心原理是制造热量缺口，建议每日热量缺口在 300-500 大卡，避免过度节食导致基础代谢下降。",
    "蛋白质摄入建议每公斤体重 1.6-2.2 克，有助于在减脂期间保持肌肉量并增加饱腹感。",
    "HIIT（高强度间歇训练）适合时间有限的人群，但每周不宜超过 3 次，每次需留出充分恢复时间。",
    "中国成人 BMI 正常范围为 18.5-23.9；理想体脂率：男性 15%-20%，女性 20%-25%。",
    "睡眠不足会导致瘦素与胃饥饿素失衡，引起食欲增加，建议每晚保证 7-9 小时睡眠。",
    "力量训练能提高静息基础代谢率，建议每周进行 2-3 次抗阻训练，每次 40-60 分钟。",
    "水分摄入建议每天 2000-3000ml，运动出汗后需适当补充电解质。",
    "减脂期主食建议以粗粮为主（燕麦、糙米、玉米、薯类），控制精制碳水摄入。",
    "力竭或关节疼痛是过度训练信号，出现时应立即减量并休息，避免运动损伤。",
    "体重波动受水分、盐分、生理周期影响，建议每周固定时间空腹称重，关注趋势而非单日数值。",
    "膳食纤维有助于控制血糖和饱腹感，建议每天摄入 25-30 克膳食纤维。",
    "减脂期每天饮水不少于 2000ml，可代谢废物并辅助脂肪分解。",
    "力量训练后 30 分钟内补充蛋白质与碳水，有利于肌肉恢复与糖原合成。",
]


def build_knowledge_base():
    embeddings = OpenAIEmbeddings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    docs = [Document(page_content=t) for t in HEALTH_KNOWLEDGE]
    split_docs = splitter.split_documents(docs)
    vectorstore = Chroma.from_documents(
        split_docs, embeddings, persist_directory=PERSIST_DIR
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})
