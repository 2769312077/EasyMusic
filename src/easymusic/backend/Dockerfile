FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg fluidsynth fluid-soundfont-gm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . /app/src/easymusic/backend

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "easymusic.backend:app", "--host", "0.0.0.0", "--port", "8000"]