FROM python:3.12-slim

LABEL description="Data quality monitoring for MeetingBank transcription service"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

ENV OS_AUTH_URL=""
ENV OS_PROJECT_ID=""
ENV OS_AUTH_TOKEN=""
ENV OS_STORAGE_URL=""
ENV OS_REGION="CHI@TACC"
ENV MLFLOW_TRACKING_URI="http://mlflow:5000"

CMD ["python3", "--help"]
