FROM python:3.12-slim

WORKDIR /app

# Chromium 설치 (ARM/AMD 모두 지원)
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]