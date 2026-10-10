from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .assistant import Assistant, GeminiAdapter, load_faq
from .config import Settings
from .parking import DEMO_NOTICE, DemoDataAdapter


class HistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=12)


class SupportMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        body = bytearray()
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            more = message.get("more_body", False)
            if len(body) > 32768:
                await self._error(send, 413, "REQUEST_TOO_LARGE", "So‘rov hajmi 32 KiB dan oshmasligi kerak.", request_id)
                return

        client = scope.get("client")
        ip = client[0] if client else "unknown"
        path = scope.get("path", "")
        key = f"{ip}:{'chat' if path == '/api/v1/assistant/chat' else 'api'}"
        limit = 10 if key.endswith(":chat") else 60
        now = time.monotonic()
        if len(self.requests) > 10000:
            self.requests = defaultdict(list, {
                bucket: ticks for bucket, ticks in self.requests.items()
                if ticks and now - ticks[-1] < 60
            })
        recent = [tick for tick in self.requests[key] if now - tick < 60]
        if len(recent) >= limit:
            self.requests[key] = recent
            await self._error(send, 429, "RATE_LIMITED", "So‘rovlar limiti vaqtincha tugadi.", request_id)
            return
        recent.append(now)
        self.requests[key] = recent

        sent = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return {"type": "http.disconnect"}

        async def with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, replay, with_request_id)

    @staticmethod
    async def _error(send: Send, status: int, code: str, message: str, request_id: str) -> None:
        payload = json.dumps({"error": {"code": code, "message": message}, "mode": "demo", "request_id": request_id}, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json; charset=utf-8"), (b"content-length", str(len(payload)).encode()), (b"x-request-id", request_id.encode())]})
        await send({"type": "http.response.body", "body": payload})


def create_app(
    settings: Settings | None = None,
    adapter: DemoDataAdapter | None = None,
    gemini: GeminiAdapter | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
    demo = adapter or DemoDataAdapter(datetime.fromisoformat(config.demo_now))
    provider = gemini or GeminiAdapter(config)
    articles = load_faq()
    assistant = Assistant(demo, provider, articles)
    app = FastAPI(title="123YUK AI Support API", version="1.0.0", docs_url="/docs", redoc_url=None)
    app.state.assistant = assistant
    app.state.adapter = demo
    app.add_middleware(SupportMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "INVALID_REQUEST", "message": "So‘rov qiymatlarini tekshiring."}, "mode": "demo", "request_id": request.state.request_id},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, _: Exception) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "INTERNAL_ERROR", "message": "Xizmatda ichki xatolik yuz berdi."}, "mode": "demo", "request_id": request.state.request_id},
            status_code=500,
        )

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready() -> dict[str, Any]:
        return {"status": "ready", "mode": "demo", "dependencies": {"demo_data": "ready", "faq": "ready", "gemini": provider.status}}

    @app.get("/api/v1/parking/status")
    async def parking_status(request: Request) -> dict[str, Any]:
        return {**demo.parking_status(), "request_id": request.state.request_id}

    @app.get("/api/v1/parking/metrics")
    async def parking_metrics(request: Request) -> dict[str, Any]:
        return {**demo.metrics(), "request_id": request.state.request_id}

    @app.post("/api/v1/assistant/chat")
    async def chat(body: ChatRequest, request: Request) -> dict[str, Any]:
        result = await assistant.chat(body.message, [turn.model_dump() for turn in body.history])
        return {**result, "request_id": request.state.request_id}

    @app.get("/api/v1/assistant/capabilities")
    async def capabilities() -> dict[str, Any]:
        return {
            "mode": "demo",
            "supported_intents": ["PARKING_STATUS", "PARKING_DURATION", "QUEUE_STATUS", "QUEUE_FORECAST", "FAQ_LOOKUP", "GREETING"],
            "tools": ["get_parking_status", "get_parking_metrics", "search_faq"],
            "queue_ids": ["loading", "unloading", "other"],
            "gemini": {"enabled": provider.status == "configured", "model": config.gemini_model, "status": provider.status},
            "real_data_enabled": False,
            "demo_notice": DEMO_NOTICE,
        }

    return app


app = create_app()
