"""prophet-mesh conductor — the OpenAI-compatible gateway in front of the vLLM seats.

This is the piece the k8s manifests expect (`uvicorn src.prophet_mesh.api:app`) and that
Noetica's "Prophet Cloud Mesh" opt-in talks to. A client POSTs /v1/chat/completions with
`model="prophet-mesh"` (or a role name, or a raw model id); the conductor picks the seat,
maps it to a backend vLLM, and proxies the OpenAI request there — streaming passthrough.

Seat routing is config-driven (SEAT_BACKENDS), so it degrades gracefully: with a single
backend it's a faithful proxy; add seats and it conducts across the choir. It NEVER invents
a completion — it forwards to a real serving backend, so there's no "vaporware alias" 404.

Env:
  SEAT_BACKENDS   JSON: {"<seat>": {"url": "http://host:8000/v1", "model": "<real-hf-id>"}, ...}
                  Must include a "default" seat. Example (single T4 vLLM):
                  {"default": {"url":"http://mesh-vllm.serving.svc:8000/v1","model":"Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"}}
  MESH_AUTH_TOKEN Optional bearer the client must present (Authorization: Bearer <token>).
  POLICY_PATH     Optional path to model-task-policy.yaml (for family metadata / /v1/models).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

# ── Seat routing config ───────────────────────────────────────────────────────
_DEFAULT_BACKENDS = {
    "default": {
        "url": os.environ.get("MESH_DEFAULT_URL", "http://mesh-vllm.serving.svc:8000/v1"),
        "model": os.environ.get("MESH_DEFAULT_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"),
    }
}


def _load_backends() -> dict[str, dict[str, str]]:
    raw = os.environ.get("SEAT_BACKENDS", "").strip()
    if not raw:
        return dict(_DEFAULT_BACKENDS)
    try:
        parsed = json.loads(raw)
        if "default" not in parsed:
            # Fail loud in logs but stay servable on the default so a bad config doesn't 500 every turn.
            print("[conductor] WARN: SEAT_BACKENDS has no 'default' seat; adding built-in default")
            parsed["default"] = _DEFAULT_BACKENDS["default"]
        return parsed
    except json.JSONDecodeError as exc:  # pragma: no cover - config error path
        print(f"[conductor] WARN: SEAT_BACKENDS is not valid JSON ({exc}); using built-in default")
        return dict(_DEFAULT_BACKENDS)


BACKENDS = _load_backends()
AUTH_TOKEN = os.environ.get("MESH_AUTH_TOKEN", "").strip()

# Lightweight seat selection: a client may target a seat explicitly via the model field
# ("code" / "reasoning" / "vision" / …). "prophet-mesh" (or unknown/blank) → route by a
# cheap content heuristic, else the default seat. A raw HF id passes straight through.
_CODE_HINTS = ("code", "```", "def ", "function ", "class ", "import ", "compile", "bug", "refactor", "stack trace")
_REASON_HINTS = ("prove", "theorem", "step by step", "derive", "why does", "reason", "plan the")


def _pick_seat(model: str, messages: list[dict[str, Any]]) -> str:
    m = (model or "").strip().lower()
    if m in BACKENDS:                       # explicit seat name
        return m
    if m and m not in ("prophet-mesh", "auto", "default"):
        return "__passthrough__"            # caller gave a concrete model id — honor it verbatim
    text = " ".join(str(x.get("content", "")) for x in messages[-3:]).lower()
    if "code" in BACKENDS and any(h in text for h in _CODE_HINTS):
        return "code"
    if "reasoning" in BACKENDS and any(h in text for h in _REASON_HINTS):
        return "reasoning"
    return "default"


app = FastAPI(title="prophet-mesh conductor", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "seats": sorted(BACKENDS.keys())}


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    now = int(time.time())
    data = [{"id": "prophet-mesh", "object": "model", "created": now, "owned_by": "prophet-mesh"}]
    data += [{"id": s, "object": "model", "created": now, "owned_by": "prophet-mesh"} for s in BACKENDS]
    return {"object": "list", "data": data}


def _check_auth(request: Request) -> None:
    if not AUTH_TOKEN:
        return
    header = request.headers.get("authorization", "")
    if header != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
    _check_auth(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="body must be JSON")

    messages = body.get("messages") or []
    seat = _pick_seat(body.get("model", ""), messages)

    if seat == "__passthrough__":
        seat_cfg = BACKENDS["default"]           # unknown model id → serve on the default backend as-is
        upstream_model = body.get("model")
    else:
        seat_cfg = BACKENDS.get(seat, BACKENDS["default"])
        upstream_model = seat_cfg["model"]

    upstream = dict(body)
    upstream["model"] = upstream_model           # rewrite to the seat's REAL served model id
    url = seat_cfg["url"].rstrip("/") + "/chat/completions"
    stream = bool(body.get("stream"))

    async def _proxy_stream():
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            async with client.stream("POST", url, json=upstream) as resp:
                if resp.status_code >= 400:
                    detail = (await resp.aread()).decode("utf-8", "replace")[:500]
                    yield f"data: {json.dumps({'error': {'message': f'seat {seat}: {detail}', 'code': resp.status_code}})}\n\n".encode()
                    yield b"data: [DONE]\n\n"
                    return
                async for chunk in resp.aiter_raw():
                    yield chunk

    if stream:
        return StreamingResponse(_proxy_stream(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(url, json=upstream)
    if resp.status_code >= 400:
        return JSONResponse(
            status_code=resp.status_code,
            content={"error": {"message": f"seat {seat}: {resp.text[:500]}", "code": resp.status_code}},
        )
    out = resp.json()
    # Surface which seat conducted this turn (observability; harmless to OpenAI clients).
    if isinstance(out, dict):
        out.setdefault("prophet_mesh", {})["seat"] = seat
    return JSONResponse(content=out)
