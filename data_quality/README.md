# Data Quality Monitoring

Three-stage data quality evaluation system for the transcription service.
All results logged to the shared MLflow instance.

## Three Evaluation Points

### 1. Ingestion Validator (`01_ingestion_validator.py`)
Runs at data ingestion from HuggingFace — before anything enters object storage.

**What it checks:**
- Schema completeness (required fields: meeting_id, transcript)
- Audio validity (WAV format, duration 1-600s, sample rate ≥ 8kHz)
- Transcript sanity (length bounds, ASCII ratio, repetition detection)
- Checksum integrity (MD5 per file)
- Duplicate detection (same meeting_id not ingested twice)

**Gate:** Pipeline stops if >20% of records are quarantined.
**Justification:** >20% failure rate indicates a systemic upstream problem
(corrupted dataset, format change) rather than isolated bad samples.

---

### 2. Training Set Validator (`02_training_set_validator.py`)
Runs after batch pipeline compiles a dataset — before training starts.

**What it checks:**
- Minimum size (≥10 train, ≥3 eval samples)
- Data leakage (no meeting_id in multiple splits) ← hard fail always
- Synthetic data ratio (≤80% synthetic in training)
- Speaker balance (no speaker >50% of training)
- Vocabulary coverage (OOV rate between train/eval)

**Gate:** Hard fail on leakage or insufficient size. Warnings on balance issues.
**Justification:** Leakage silently inflates eval metrics — it must be a hard
fail. Size and balance gates prevent training on degenerate datasets that would
waste compute and produce unreliable models.

---

### 3. Drift Monitor (`03_drift_monitor.py`)
Runs continuously in production — every 5 minutes.

**What it monitors:**
- Audio duration distribution (mean, std, percentiles)
- Transcript length distribution
- Feature mean/variance shift
- Request volume anomalies

**Drift detection:** Relative change from training reference distribution.
Alerts at 30% drift (WARNING) and 60% drift (CRITICAL).

**Justification:** MeetingBank covers specific US cities. Production traffic
may include different meeting types, accents, or recording conditions.
Distribution shift degrades WER without any visible error — only monitoring
catches this.

---

## Running

### Setup
```bash
cp .env.example .env
# Fill in your OS_AUTH_TOKEN and OS_STORAGE_URL from: source openrc && env | grep OS_
```

### Run individually
```bash
# 1. After ingestion
docker compose run --rm ingestion-validator

# 2. Before retraining
docker compose run --rm training-set-validator

# 3. Start drift monitor (always-on)
docker compose up -d drift-monitor
```

### Run full stack
```bash
docker compose up -d
```

### View results in MLflow
```
http://localhost:5000
Experiments:
  - data_quality_ingestion       ← ingestion validation runs
  - data_quality_training_set    ← training set validation runs
  - data_quality_drift_monitor   ← drift detection runs
```

---

## Integration with Team's Docker Compose

Merge the service definitions from `docker-compose.yml` into your team's
main `docker-compose.yml`. Key integration points:

**Ingestion pipeline** should call ingestion-validator after uploading:
```yaml
ingestion-validator:
  depends_on:
    ingest:
      condition: service_completed_successfully
```

**Training pipeline** should gate on training-set-validator:
```yaml
training:
  depends_on:
    training-set-validator:
      condition: service_completed_successfully
```

**Drift monitor** runs alongside the serving stack:
```yaml
drift-monitor:
  depends_on:
    - transcription-service
    - mlflow
```

**Important:** Use the shared MLflow instance — do not run a separate one.
The drift monitor, training validator, and model training all log to the
same MLflow server so all data quality and model quality metrics are
visible in one place.

---

## MLflow Metrics Logged

| Experiment | Key Metrics |
|---|---|
| data_quality_ingestion | pass_rate, quarantine_rate, avg_audio_duration, quality_gate_passed |
| data_quality_training_set | train_count, synthetic_ratio, oov_rate, leakage_detected, quality_gate_passed |
| data_quality_drift_monitor | max_drift_score, n_alerts, duration_mean_live, feature_mean_live |
