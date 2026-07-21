"""
OpenAI-Compatible API Server

Provides:
- POST /v1/chat/completions — OpenAI Chat Completions (streaming via SSE)
- POST /v1/responses — OpenAI Responses API
- GET  /v1/models — List available models
- GET  /health — Health check
- GET  /status — System status
- POST /v1/tasks — Create async task
- GET  /v1/tasks/{id} — Get task status

Uses FastAPI for the HTTP layer.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from superagent.gateway.router import Channel, InboundMessage, MessageRouter

logger = structlog.get_logger()


def create_app(
    router: MessageRouter,
    auth_token: str | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title="SUPERAGENT API",
        description="OpenAI-compatible API for SUPERAGENT agent system",
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store router reference
    app.state.router = router
    app.state.auth_token = auth_token

    # ── Auth Middleware ──────────────────────────────────────────

    async def _check_auth(authorization: str | None) -> None:
        """Check API authentication."""
        if not auth_token:
            return  # no auth configured
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        token = authorization.replace("Bearer ", "")
        if token != auth_token:
            raise HTTPException(status_code=401, detail="Invalid API token")

    # ── Health Endpoints ────────────────────────────────────────

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/health/detailed")
    async def health_detailed() -> dict[str, Any]:
        stats = router.get_stats()
        queen_status = {}
        if router._queen:
            queen_status = await router._queen.get_status()
        return {
            "status": "ok",
            "version": "0.1.0",
            "router": stats,
            "queen": queen_status,
        }

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return router.get_stats()

    # ── OpenAI-Compatible Endpoints ─────────────────────────────

    @app.get("/v1/models")
    async def list_models(authorization: str | None = Header(None)) -> dict[str, Any]:
        await _check_auth(authorization)
        return {
            "object": "list",
            "data": [
                {
                    "id": "superagent",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "superagent",
                    "permission": [],
                },
                {
                    "id": "superagent-market",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "superagent",
                    "permission": [],
                },
                {
                    "id": "superagent-info",
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "superagent",
                    "permission": [],
                },
            ],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        authorization: str | None = Header(None),
    ) -> Any:
        """
        OpenAI-compatible chat completions endpoint.

        Accepts:
        - model: "superagent" (routes through Queen)
        - messages: conversation history
        - stream: true/false (SSE streaming)
        """
        await _check_auth(authorization)

        body = await request.json()
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        model = body.get("model", "superagent")

        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # Extract the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Build inbound message for the router
        inbound = InboundMessage(
            channel=Channel.API,
            channel_message_id=str(uuid.uuid4()),
            user_id="api_user",
            chat_id="api",
            content=last_message,
            metadata={"model": model, "full_messages": messages},
        )

        if stream:
            return StreamingResponse(
                _stream_chat(router, inbound, model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # Non-streaming response
        response = await router.handle_message(inbound)
        content = response.content if response else "No response"

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": response.metadata.get("tokens_used", 0) if response else 0,
            },
        }

    async def _stream_chat(
        router: MessageRouter,
        inbound: InboundMessage,
        model: str,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions via SSE."""
        response = await router.handle_message(inbound)
        content = response.content if response else "No response"

        # Stream the response in chunks
        chunk_size = 20
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            data = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.02)  # simulate streaming

        # Final chunk
        final = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    # ── Task Endpoints ──────────────────────────────────────────

    # In-memory task store (would use database in production)
    _tasks: dict[str, dict[str, Any]] = {}

    @app.post("/v1/tasks")
    async def create_task(
        request: Request,
        authorization: str | None = Header(None),
    ) -> dict[str, Any]:
        """Create an async task."""
        await _check_auth(authorization)

        body = await request.json()
        task_description = body.get("task", "")
        priority = body.get("priority", "medium")

        if not task_description:
            raise HTTPException(status_code=400, detail="No task description provided")

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        _tasks[task_id] = {
            "id": task_id,
            "task": task_description,
            "priority": priority,
            "status": "pending",
            "created_at": time.time(),
            "result": None,
        }

        # Process task in background
        asyncio.create_task(_process_task(router, task_id, task_description))

        return {
            "id": task_id,
            "status": "pending",
            "created_at": _tasks[task_id]["created_at"],
        }

    @app.get("/v1/tasks/{task_id}")
    async def get_task(
        task_id: str,
        authorization: str | None = Header(None),
    ) -> dict[str, Any]:
        """Get task status."""
        await _check_auth(authorization)

        task = _tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    async def _process_task(
        router: MessageRouter,
        task_id: str,
        description: str,
    ) -> None:
        """Process an async task."""
        try:
            _tasks[task_id]["status"] = "running"

            inbound = InboundMessage(
                channel=Channel.API,
                channel_message_id=str(uuid.uuid4()),
                user_id="api_task",
                chat_id=f"task_{task_id}",
                content=description,
            )

            response = await router.handle_message(inbound)

            _tasks[task_id]["status"] = "completed"
            _tasks[task_id]["result"] = response.content if response else "No result"
            _tasks[task_id]["completed_at"] = time.time()

        except Exception as e:
            _tasks[task_id]["status"] = "failed"
            _tasks[task_id]["error"] = str(e)
            logger.error("task_failed", task_id=task_id, error=str(e))

    return app
