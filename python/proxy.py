import json
import time
import uuid
import httpx
import asyncio
from typing import AsyncIterator

from config import (
    get_access_token,
    API_BASE_URL,
    ATOMCODE_USER_AGENT,
    fetch_codingplan_models,
)
from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    Choice,
    ChoiceMessage,
    DeltaMessage,
    StreamChoice,
    Usage,
)

REQUEST_TIMEOUT = 120.0


def _generate_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:29]}"


def _build_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": ATOMCODE_USER_AGENT,
    }


def _transform_request(req: ChatCompletionRequest) -> dict:
    messages = []
    for msg in req.messages:
        m = {"role": msg.role.value, "content": msg.content}
        if msg.reasoning_content:
            m["reasoning_content"] = msg.reasoning_content
        if msg.tool_calls:
            m["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            m["tool_call_id"] = msg.tool_call_id
        if msg.name:
            m["name"] = msg.name
        messages.append(m)

    payload = {
        "model": req.model,
        "messages": messages,
        "stream": req.stream,
    }

    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.top_p is not None:
        payload["top_p"] = req.top_p
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    if req.stop is not None:
        payload["stop"] = req.stop
    if req.presence_penalty is not None:
        payload["presence_penalty"] = req.presence_penalty
    if req.frequency_penalty is not None:
        payload["frequency_penalty"] = req.frequency_penalty
    if req.tools is not None:
        payload["tools"] = req.tools
    if req.tool_choice is not None:
        payload["tool_choice"] = req.tool_choice
    if req.response_format is not None:
        payload["response_format"] = req.response_format
    if req.seed is not None:
        payload["seed"] = req.seed
    if req.logprobs is not None:
        payload["logprobs"] = req.logprobs
    if req.top_logprobs is not None:
        payload["top_logprobs"] = req.top_logprobs

    return payload


def _parse_non_stream_response(
    resp_json: dict, request_model: str
) -> ChatCompletionResponse:
    choices = []
    for i, ch in enumerate(resp_json.get("choices", [])):
        msg_data = ch.get("message", {})
        choice_msg = ChoiceMessage(
            role=msg_data.get("role", "assistant"),
            content=msg_data.get("content"),
            reasoning_content=msg_data.get("reasoning_content"),
            tool_calls=msg_data.get("tool_calls"),
        )
        choices.append(
            Choice(
                index=i,
                message=choice_msg,
                finish_reason=ch.get("finish_reason", "stop"),
            )
        )

    usage_data = resp_json.get("usage", {})
    usage = Usage(
        prompt_tokens=usage_data.get("prompt_tokens", 0),
        completion_tokens=usage_data.get("completion_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0),
    )

    return ChatCompletionResponse(
        id=resp_json.get("id", _generate_id()),
        created=resp_json.get("created", int(time.time())),
        model=request_model,
        choices=choices,
        usage=usage,
    )


async def chat_completion(req: ChatCompletionRequest) -> ChatCompletionResponse:
    api_key = get_access_token()
    if not api_key:
        raise ValueError("未找到 Token，请先运行 atomcode login 或设置 ATOMCODE_API_KEY 环境变量")

    url = f"{API_BASE_URL}/chat/completions"
    headers = _build_headers(api_key)
    payload = _transform_request(req)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        resp_json = resp.json()

    return _parse_non_stream_response(resp_json, req.model)


async def chat_completion_stream(
    req: ChatCompletionRequest,
) -> AsyncIterator[str]:
    api_key = get_access_token()
    if not api_key:
        raise ValueError("未找到 Token，请先运行 atomcode login 或设置 ATOMCODE_API_KEY 环境变量")

    url = f"{API_BASE_URL}/chat/completions"
    headers = _build_headers(api_key)
    payload = _transform_request(req)
    payload["stream"] = True

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=False) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(data)
                        stream_chunk = _parse_stream_chunk(chunk, req.model)
                        yield f"data: {stream_chunk.model_dump_json()}\n\n"
                    except json.JSONDecodeError:
                        yield f"{line}\n\n"
                else:
                    yield f"{line}\n\n"


def _parse_stream_chunk(chunk: dict, request_model: str) -> ChatCompletionStreamResponse:
    choices = []
    for i, ch in enumerate(chunk.get("choices", [])):
        delta_data = ch.get("delta", {})
        delta = DeltaMessage(
            role=delta_data.get("role"),
            content=delta_data.get("content"),
            reasoning_content=delta_data.get("reasoning_content"),
            tool_calls=delta_data.get("tool_calls"),
        )
        choices.append(
            StreamChoice(
                index=i,
                delta=delta,
                finish_reason=ch.get("finish_reason"),
            )
        )

    usage_data = chunk.get("usage")
    usage = None
    if usage_data:
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

    return ChatCompletionStreamResponse(
        id=chunk.get("id", _generate_id()),
        created=chunk.get("created", int(time.time())),
        model=request_model,
        choices=choices,
        usage=usage,
    )
