# Edge AI Benchmark Suite — CPU-базовый образ.
#
# Для GPU/TensorRT-бенчмарков на Jetson/десктопе с NVIDIA GPU замените базовый
# образ на соответствующий NVIDIA (nvcr.io/nvidia/l4t-* для Jetson,
# nvidia/cuda для десктопа), доустановите tensorrt/cuda-python поверх него
# (см. INSTALL.md — готовые wheel'ы NVIDIA, без компиляции) и запускайте
# контейнер с `--gpus all` (десктоп) или nvidia-container-runtime (Jetson) —
# иначе GPU/TensorRT будут недоступны внутри контейнера (фреймворк корректно
# это задетектирует и пропустит соответствующие форматы).

FROM python:3.11-slim

# libgl1/libglib2.0-0 нужны opencv-python для работы без X-сервера.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY edge_ai_benchmark ./edge_ai_benchmark
COPY pyproject.toml .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "edge_ai_benchmark"]
CMD ["run", "--config", "edge_ai_benchmark/configs/default.yaml"]
