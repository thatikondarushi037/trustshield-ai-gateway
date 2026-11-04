"""Bound request buffering and prevent raw exception/validation output."""
from starlette.responses import JSONResponse
from src.settings import MAX_BODY_BYTES


class HttpSafety:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid request length"}, 400)(scope, receive, send)
        if declared < 0 or declared > MAX_BODY_BYTES:
            return await JSONResponse({"detail": "Request body too large"}, 413)(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                return await JSONResponse({"detail": "Request body too large"}, 413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        consumed, started = False, False

        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        async def safe_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff")]
            await send(message)
        try:
            await self.app(scope, replay, safe_send)
        except Exception:
            # Do not rethrow into Uvicorn's traceback logger with private exception text.
            if not started:
                await JSONResponse({"detail": "Service unavailable"}, 500)(scope, replay, safe_send)
