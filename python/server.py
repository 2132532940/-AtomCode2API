import time
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from config import (
    SERVER_HOST,
    SERVER_PORT,
    get_access_token,
    fetch_codingplan_models,
    get_all_model_ids,
    GITCODE_API_BASE,
)
from model_list import AVAILABLE_MODELS, NEEDS_PRO_MODELS
from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelObject,
    ModelListResponse,
)
from proxy import chat_completion, chat_completion_stream

app = FastAPI(
    title="AtomCode2API",
    description="AtomCode CodingPlan -> OpenAI 兼容 API",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/models")
async def list_models():
    now = int(time.time())
    model_objects = []
    for model_id, info in AVAILABLE_MODELS.items():
        model_objects.append(
            ModelObject(
                id=model_id,
                created=now,
                owned_by=f"atomcode-{info['provider']}",
            )
        )
    return ModelListResponse(data=model_objects)


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    if model_id in AVAILABLE_MODELS:
        info = AVAILABLE_MODELS[model_id]
        return ModelObject(
            id=model_id,
            created=int(time.time()),
            owned_by=f"atomcode-{info['provider']}",
        )
    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")


@app.post("/v1/chat/completions")
async def create_chat_completion(req: ChatCompletionRequest):
    if req.model in NEEDS_PRO_MODELS:
        raise HTTPException(
            status_code=403,
            detail=f"模型 {req.model} 需要 CodingPlan Pro，当前为 Lite 计划",
        )
    try:
        if req.stream:
            return StreamingResponse(
                chat_completion_stream(req),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        result = await chat_completion(req)
        return JSONResponse(content=result.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上游请求失败: {str(e)}")


@app.post("/chat/completions")
async def create_chat_completion_no_v1(req: ChatCompletionRequest):
    return await create_chat_completion(req)


@app.get("/v1/codingplan/models")
async def codingplan_models():
    token = get_access_token()
    if not token:
        raise HTTPException(status_code=401, detail="未登录，请先运行 atomcode login")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITCODE_API_BASE}/coding-plan/models",
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/codingplan/status")
async def codingplan_status():
    token = get_access_token()
    if not token:
        raise HTTPException(status_code=401, detail="未登录，请先运行 atomcode login")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITCODE_API_BASE}/coding-plan/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/health")
async def health():
    token = get_access_token()
    return {
        "status": "ok",
        "token_configured": token is not None,
        "total_models": len(AVAILABLE_MODELS),
        "service": "AtomCode2API",
    }


@app.get("/")
async def root():
    return {
        "service": "AtomCode2API",
        "version": "3.0.0",
        "total_models": len(AVAILABLE_MODELS),
        "endpoints": {
            "chat_completions": "/v1/chat/completions",
            "models": "/v1/models",
            "codingplan_models": "/v1/codingplan/models",
            "codingplan_status": "/v1/codingplan/status",
            "health": "/v1/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info",
    )
