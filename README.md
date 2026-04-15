# 职业规划智能体 · 后端

FastAPI + LangChain（OpenAI 兼容接口）提供流式对话。

## 运行

```bash
cd career-planning-backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

健康检查：`GET http://127.0.0.1:8000/api/health`

流式对话：`POST http://127.0.0.1:8000/api/chat/stream`，请求体 `{ "messages": [{ "role": "user", "content": "..." }] }`，响应为 SSE。
