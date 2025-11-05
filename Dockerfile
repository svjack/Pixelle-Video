# Pixelle-Video Docker Image
# Based on Python 3.11 slim for smaller image size

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - curl: for health checks and downloads
# - ffmpeg: for video/audio processing
# - chromium: for html2image rendering
# - fonts-noto-cjk: for CJK character support
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv --version
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies using uv
RUN /root/.local/bin/uv sync --frozen --no-dev

# Copy application code
COPY pixelle_video ./pixelle_video
COPY api ./api
COPY web ./web
COPY bgm ./bgm
COPY templates ./templates
COPY workflows ./workflows

# Create output and data directories
RUN mkdir -p /app/output /app/data

# Set environment variables for html2image to use chromium
ENV BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
ENV CHROME_BIN=/usr/bin/chromium

# Expose ports
# 8000: API service
# 8501: Web UI service
EXPOSE 8000 8501

# Default command (can be overridden in docker-compose)
CMD ["/root/.local/bin/uv", "run", "python", "api/app.py"]

