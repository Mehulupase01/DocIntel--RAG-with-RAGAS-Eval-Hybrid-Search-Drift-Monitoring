FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.5.21
COPY apps/dashboard/pyproject.toml ./
RUN uv sync --frozen --no-dev || uv sync --no-dev
COPY apps/dashboard/ ./
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
