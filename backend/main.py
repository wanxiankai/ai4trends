# main.py
# 导入必要的库
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import datetime

# --- Pydantic 模型定义 (用于数据校验和序列化) ---
# 定义聊天消息的结构
class ChatMessage(BaseModel):
    message: str

# 定义配置项的结构
class Config(BaseModel):
    trending_language: str
    schedule_interval_hours: int

# 定义单个分析结果的结构
class AnalysisResult(BaseModel):
    id: int
    repo_name: str
    repo_url: str
    analysis_timestamp: datetime.datetime
    one_liner_summary: str
    tech_stack: List[str]
    key_features: List[str]
    community_focus: List[str]

# --- 创建 FastAPI 应用实例 ---
app = FastAPI(
    title="GitHub Trending AI Analyst Backend",
    description="为GitHub热点趋势分析助手提供API服务",
    version="0.1.0",
)

# --- 中间件配置 (CORS) ---
# 配置跨域资源共享 (CORS)，允许前端应用(例如 http://localhost:5173)访问后端API
origins = [
    "http://localhost",
    "http://localhost:5173", # 默认的Vite React开发服务器地址
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # 允许所有HTTP方法
    allow_headers=["*"], # 允许所有HTTP头
)


# --- 模拟数据库/数据存储 ---
# 在真实应用中，这些数据会从数据库中读取
mock_db = {
    "config": {
        "trending_language": "Python",
        "schedule_interval_hours": 1,
    },
    "results": [
        {
            "id": 1,
            "repo_name": "Significant-Gravitas/AutoGPT",
            "repo_url": "https://github.com/Significant-Gravitas/AutoGPT",
            "analysis_timestamp": datetime.datetime.now() - datetime.timedelta(days=1),
            "one_liner_summary": "一个旨在让GPT-4完全自主运行的实验性开源尝试。",
            "tech_stack": ["Python", "GPT-4", "Pinecone", "Redis"],
            "key_features": ["🤖 自主AI智能体", "分解复杂任务", "长期与短期记忆管理"],
            "community_focus": ["API成本过高", "安装配置复杂", "对新功能提出建议"],
        },
        {
            "id": 2,
            "repo_name": "microsoft/JARVIS",
            "repo_url": "https://github.com/microsoft/JARVIS",
            "analysis_timestamp": datetime.datetime.now() - datetime.timedelta(days=1),
            "one_liner_summary": "一个连接语言模型与机器学习社区，以解决AI任务的协作系统。",
            "tech_stack": ["Python", "Hugging Face", "PyTorch", "OpenAI"],
            "key_features": ["🤝 模型协作系统", "任务规划与执行", "集成多种AI模型"],
            "community_focus": ["模型兼容性问题", "需要更详细的文档", "执行效率优化"],
        },
        {
            "id": 3,
            "repo_name": "shadcn/ui",
            "repo_url": "https://github.com/shadcn/ui",
            "analysis_timestamp": datetime.datetime.now() - datetime.timedelta(days=1),
            "one_liner_summary": "使用Tailwind CSS构建的可重用、美观且易于访问的React组件。",
            "tech_stack": ["TypeScript", "React", "Tailwind CSS", "Radix UI"],
            "key_features": ["🎨 设计精美", "高度可定制", "代码即组件，非库"],
            "community_focus": ["新组件请求", "对不同框架的支持", "主题和样式定制"],
        },
    ]
}

# --- API 端点 (Endpoints) ---

@app.get("/")
def read_root():
    """根路径，返回一个欢迎信息"""
    return {"message": "欢迎使用 GitHub 热点趋势分析助手后端 API"}

@app.get("/api/config", response_model=Config)
async def get_config():
    """获取当前的任务配置"""
    return mock_db["config"]

@app.get("/api/results", response_model=List[AnalysisResult])
async def get_results():
    """获取最新的分析结果列表"""
    return mock_db["results"]

@app.post("/api/chat")
async def handle_chat(chat_message: ChatMessage):
    """
    处理来自前端的聊天消息。
    这是一个模拟的端点，它会解析用户的输入并更新模拟的配置。
    在真实应用中，这里会调用AI模型来理解用户意图。
    """
    message = chat_message.message.lower()
    response_text = "抱歉，我不太理解你的意思。你可以尝试说：'追踪[语言]'或'频率改为[数字]小时'。"

    # 模拟AI意图识别
    if '追踪' in message or 'track' in message:
        languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
        found_lang = next((lang for lang in languages if lang in message), None)
        if found_lang:
            mock_db["config"]["trending_language"] = found_lang
            response_text = f"好的！我已经将追踪的语言更新为 **{found_lang}**。下次更新将分析该语言的热点项目。"
    elif '小时' in message or '频率' in message or 'interval' in message:
        import re
        match = re.search(r'\d+', message)
        if match:
            hours = int(match.group(0))
            if hours > 0:
                mock_db["config"]["schedule_interval_hours"] = hours
                response_text = f"收到！我已经将任务更新频率调整为每 **{hours}** 小时一次。"

    return {"reply": response_text}

# --- 如何运行 ---
# 1. 保存此文件为 main.py
# 2. 安装必要的库:
#    pip install fastapi "uvicorn[standard]"
# 3. 在终端中运行:
#    uvicorn main:app --reload
#
#    应用将在 http://127.0.0.1:8000 运行
