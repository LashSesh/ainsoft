"""Payload generators and transformers for API mimicry and steganography."""

from __future__ import annotations

import random
import time
from typing import Any, Dict


def fake_api_request_generator() -> Dict[str, Any]:
    """Generate dummy API-like request payloads."""

    apis = [
        {
            "protocol": "https",
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {"Authorization": "Bearer ..."},
            "body": '{"model":"gpt-3.5","prompt":"Hi"}',
        },
        {
            "protocol": "https",
            "method": "GET",
            "url": "https://slack.com/api/conversations.list",
            "headers": {"Authorization": "Bearer ..."},
            "body": None,
        },
        {
            "protocol": "https",
            "method": "POST",
            "url": "https://api.telegram.org/botTOKEN/sendMessage",
            "headers": {},
            "body": '{"chat_id":123,"text":"Hello"}',
        },
    ]
    payload = random.choice(apis).copy()
    payload["timestamp"] = time.time()
    return payload


def http_builder_transformer(payload: Dict[str, Any]) -> str:
    """Convert the payload into a raw HTTP request string."""

    if "method" not in payload or "url" not in payload:
        return str(payload)

    request_lines = [f"{payload['method']} {payload['url']} HTTP/1.1"]
    for header, value in payload.get("headers", {}).items():
        request_lines.append(f"{header}: {value}")
    request_lines.append("")
    if payload.get("body"):
        request_lines.append(str(payload["body"]))
    return "\r\n".join(request_lines)


def steganography_transformer(payload: Any) -> str:
    """Encode the payload using zero-width character steganography."""

    data = str(payload)
    binary_stream = "".join(format(ord(char), "08b") for char in data)
    zero_width = ["\u200B" if bit == "1" else "\u200C" for bit in binary_stream]
    return "".join(zero_width)


__all__ = [
    "fake_api_request_generator",
    "http_builder_transformer",
    "steganography_transformer",
]
