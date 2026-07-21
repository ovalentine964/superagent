"""
Communication Tools

Provides:
- Message sending to various channels
- Notification management
- Webhook dispatch
- Email integration (optional)
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Message queue for cross-channel delivery
_message_queue: list[dict[str, Any]] = []


def register(registry: Any) -> None:
    """Register communication tools with the tool registry."""

    @registry.register_decorator(
        name="send_message",
        description="Send a message to a specific channel (Telegram, Discord, etc).",
        category="communication",
    )
    async def send_message(
        channel: str,
        target: str,
        message: str,
        format: str = "text",
    ) -> str:
        """
        Send a message to a channel.

        Args:
            channel: Target channel (telegram, discord, api)
            target: Target ID (chat_id, channel_id, etc)
            message: Message content
            format: Message format (text, markdown, html)
        """
        delivery = {
            "channel": channel,
            "target": target,
            "message": message,
            "format": format,
            "timestamp": time.time(),
            "status": "queued",
        }
        _message_queue.append(delivery)

        logger.info(
            "message_queued",
            channel=channel,
            target=target,
            length=len(message),
        )

        # In production, this would dispatch to the actual channel adapter
        # For now, queue it for the gateway to process
        return json.dumps({
            "status": "queued",
            "channel": channel,
            "target": target,
            "message_length": len(message),
            "queue_position": len(_message_queue),
        })

    @registry.register_decorator(
        name="notification_sender",
        description="Send a notification/alert with severity level.",
        category="communication",
    )
    async def notification_sender(
        message: str,
        severity: str = "medium",
        channels: str = "telegram",
        title: str | None = None,
    ) -> str:
        """
        Send a notification to one or more channels.

        Args:
            message: Alert message
            severity: low / medium / high / critical
            channels: Comma-separated channel list
            title: Optional alert title
        """
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🔶",
            "critical": "🚨",
        }

        emoji = severity_emoji.get(severity, "📢")
        formatted = f"{emoji} **{severity.upper()}**"
        if title:
            formatted += f": {title}"
        formatted += f"\n\n{message}"

        results = []
        for channel in channels.split(","):
            channel = channel.strip()
            result = await send_message(
                channel=channel,
                target="default",
                message=formatted,
                format="markdown",
            )
            results.append(json.loads(result))

        return json.dumps({
            "status": "sent",
            "severity": severity,
            "channels": channels,
            "results": results,
        })

    @registry.register_decorator(
        name="webhook_dispatch",
        description="Dispatch a webhook to an external URL.",
        category="communication",
    )
    async def webhook_dispatch(
        url: str,
        payload: str,
        method: str = "POST",
        headers: str | None = None,
    ) -> str:
        """
        Send a webhook to an external URL.

        Args:
            url: Target URL
            payload: JSON payload string
            method: HTTP method
            headers: JSON string of additional headers
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                header_dict = {}
                if headers:
                    header_dict = json.loads(headers)

                header_dict.setdefault("Content-Type", "application/json")

                if method.upper() == "POST":
                    response = await client.post(
                        url,
                        content=payload,
                        headers=header_dict,
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url,
                        content=payload,
                        headers=header_dict,
                    )
                else:
                    return json.dumps({"error": f"Unsupported method: {method}"})

                return json.dumps({
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 300,
                    "response": response.text[:500],
                })

            except Exception as e:
                logger.error("webhook_failed", url=url, error=str(e))
                return json.dumps({"error": str(e)})

    @registry.register_decorator(
        name="task_board",
        description="Manage tasks on the coordination board (create, update, list, complete).",
        category="coordination",
    )
    async def task_board(
        action: str,
        task_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> str:
        """
        Manage tasks on the coordination board.

        Args:
            action: create / update / list / complete / delete
            task_id: Task ID (for update/complete/delete)
            title: Task title (for create)
            description: Task description
            status: New status (for update)
            assignee: Assigned agent
        """
        # In-memory task board (would be backed by database in production)
        if not hasattr(task_board, "_tasks"):
            task_board._tasks = {}
            task_board._counter = 0

        if action == "create":
            task_board._counter += 1
            tid = f"TASK-{task_board._counter:04d}"
            task_board._tasks[tid] = {
                "id": tid,
                "title": title or "Untitled",
                "description": description or "",
                "status": "todo",
                "assignee": assignee,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            return json.dumps({"status": "created", "task": task_board._tasks[tid]}, indent=2)

        elif action == "update":
            if task_id and task_id in task_board._tasks:
                task = task_board._tasks[task_id]
                if title:
                    task["title"] = title
                if description:
                    task["description"] = description
                if status:
                    task["status"] = status
                if assignee:
                    task["assignee"] = assignee
                task["updated_at"] = time.time()
                return json.dumps({"status": "updated", "task": task}, indent=2)
            return json.dumps({"error": f"Task {task_id} not found"})

        elif action == "complete":
            if task_id and task_id in task_board._tasks:
                task_board._tasks[task_id]["status"] = "done"
                task_board._tasks[task_id]["updated_at"] = time.time()
                return json.dumps({"status": "completed", "task_id": task_id})
            return json.dumps({"error": f"Task {task_id} not found"})

        elif action == "list":
            tasks = list(task_board._tasks.values())
            return json.dumps({
                "count": len(tasks),
                "tasks": tasks,
            }, indent=2)

        elif action == "delete":
            if task_id and task_id in task_board._tasks:
                del task_board._tasks[task_id]
                return json.dumps({"status": "deleted", "task_id": task_id})
            return json.dumps({"error": f"Task {task_id} not found"})

        return json.dumps({"error": f"Unknown action: {action}"})


def get_message_queue() -> list[dict[str, Any]]:
    """Get the current message queue (for gateway processing)."""
    return _message_queue


def clear_message_queue() -> None:
    """Clear the message queue after processing."""
    _message_queue.clear()
