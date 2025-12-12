FROM python:3.11-slim
WORKDIR /app
COPY ainsoft/ ./ainsoft/
RUN pip install --no-cache-dir fastapi click uvicorn numpy PySocks PyYAML
CMD ["python", "-m", "ainsoft.interfaces.cli", "127.0.0.1", "--cycles", "3"]
