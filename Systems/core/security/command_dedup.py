from __future__ import annotations

import time
from typing import Dict, Tuple

from aiogram import BaseMiddleware
from aiogram.types import Update
from loguru import logger


class CommandDedupMiddleware(BaseMiddleware):
    """Middleware, игнорирующая повторные команды от одного чата."""

    def __init__(self, window_seconds: float = 1.5):
        super().__init__()
        self.window_seconds = window_seconds
        self._last_seen: Dict[Tuple[int, str], float] = {}
        self._logger = logger.bind(service="CommandDedupMiddleware")

    def _cleanup(self, now: float) -> None:
        expiration = now - self.window_seconds * 5
        keys_to_remove = [key for key, ts in self._last_seen.items() if ts < expiration]
        for key in keys_to_remove:
            self._last_seen.pop(key, None)

    async def __call__(self, handler, event: Update, data):
        message = getattr(event, "message", None)
        if message and message.text and message.text.strip().startswith("/"):
            chat_id = message.chat.id
            command = message.text.split()[0].split("@")[0].lower()
            now = time.monotonic()
            last_timestamp = self._last_seen.get((chat_id, command))

            if last_timestamp and now - last_timestamp < self.window_seconds:
                self._logger.warning(
                    f"Игнорирую дубликат команды '{command}' от чата {chat_id} (прошло {now - last_timestamp:.3f}s)."
                )
                return None

            self._last_seen[(chat_id, command)] = now
            self._cleanup(now)

        return await handler(event, data)

