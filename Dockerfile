FROM python:3.12-slim

LABEL maintainer="transcription-project"
LABEL description="Data pipeline for MeetingBank transcription service"

# System dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pipeline

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline scripts
COPY scripts/ ./scripts/

# Capture git SHA for lineage tracking
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# OpenStack credentials are passed in at runtime via environment variables
# Never bake credentials into the image
ENV OS_AUTH_URL=""
ENV OS_PROJECT_ID=""
ENV OS_AUTH_TOKEN=""
ENV OS_STORAGE_URL=""
ENV OS_REGION="CHI@UC"

# Default entrypoint runs full pipeline
# Override CMD to run individual stages
ENTRYPOINT ["python3", "scripts/run_pipeline.py"]
CMD ["--help"]
