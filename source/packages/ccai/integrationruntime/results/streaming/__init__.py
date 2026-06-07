"""
    .. module:: ccai.integrationruntime.results.streaming
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Package for result streaming services.

    This package provides services for streaming test results to external
    services in real-time. It supports both REST endpoint streaming and
    WebSocket-based streaming.

    .. moduleauthor:: CodeCraftX
"""

from ccai.integrationruntime.results.streaming.resultstreamer import (
    ResultStreamer,
    RestResultStreamer,
    WebSocketResultStreamer,
    create_result_streamer
)

__all__ = [
    "ResultStreamer",
    "RestResultStreamer",
    "WebSocketResultStreamer",
    "create_result_streamer"
]
