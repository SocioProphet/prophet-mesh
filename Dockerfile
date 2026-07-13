# prophet-mesh conductor — OpenAI-compatible gateway in front of the vLLM seats.
# Serves src/prophet_mesh/api.py:app on :8780 (matches infra/k8s/prophet-mesh).
FROM python:3.11-slim

WORKDIR /app
# api.py needs only these at runtime (no wheel build — avoids the hatchling backend).
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.30" "httpx>=0.27" "PyYAML>=6.0.2"

COPY src ./src
ENV PYTHONPATH=/app/src PORT=8780
EXPOSE 8780

# Reads SEAT_BACKENDS / MESH_AUTH_TOKEN / MESH_DEFAULT_URL / MESH_DEFAULT_MODEL from env.
CMD ["sh", "-c", "uvicorn prophet_mesh.api:app --host 0.0.0.0 --port ${PORT}"]
