# Async Pipeline Quick Start Guide

## Installation

First, install the required dependencies:

```bash
pip install aiosqlite httpx structlog
```

## Usage

### Option 1: Command Line Interface (Recommended for Testing)

Process jobs using the async pipeline from the command line:

```bash
# Basic usage with defaults
python -m src.cli process-async "software engineer"

# Custom configuration
python -m src.cli process-async "python developer" \
  --resume data/resume_python.txt \
  --workers 8 \
  --min-score 60 \
  --log-level INFO
```

### Option 2: FastAPI Endpoint

Use the async pipeline via the REST API:

```bash
# Start the server
uvicorn main:app --reload

# Make a request
curl -X POST "http://localhost:8000/run-query-async" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "software engineer",
    "min_score": 50
  }'
```

## Configuration Options

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--resume` | Path to resume file | data/resume.txt |
| `--workers` | Number of concurrent workers | 5 |
| `--queue-size` | Queue size for backpressure | 100 |
| `--max-concurrent` | Max concurrent API calls | 3 |
| `--llm-rate` | LLM API rate limit (per second) | 10 |
| `--email-rate` | Email API rate limit (per second) | 2 |
| `--scraper-rate` | Scraper rate limit (per second) | 30 |
| `--min-score` | Minimum match score (0-100) | 50 |
| `--log-level` | Log level (DEBUG/INFO/WARNING/ERROR) | INFO |

## Examples

### Example 1: Process Jobs with Higher Throughput

```bash
python -m src.cli process-async "senior engineer" \
  --workers 10 \
  --max-concurrent 5 \
  --queue-size 200
```

### Example 2: Conservative Processing (Respect API Limits)

```bash
python -m src.cli process-async "data scientist" \
  --workers 3 \
  --llm-rate 5 \
  --email-rate 1
```

### Example 3: High Match Score Jobs Only

```bash
python -m src.cli process-async "machine learning" \
  --min-score 75 \
  --resume data/resume_ml.txt
```

### Example 4: Debug Mode

```bash
python -m src.cli process-async "python developer" \
  --workers 2 \
  --log-level DEBUG
```

## Performance Tips

### For Small Job Volumes (<100 jobs)
```bash
python -m src.cli process-async "query" \
  --workers 3 \
  --queue-size 50
```

### For Large Job Volumes (1000+ jobs)
```bash
python -m src.cli process-async "query" \
  --workers 8 \
  --queue-size 200 \
  --max-concurrent 5
```

### For Rate-Limited APIs
```bash
python -m src.cli process-async "query" \
  --llm-rate 5 \
  --email-rate 1 \
  --scraper-rate 20
```

## Monitoring

The async pipeline provides real-time output:

```
Starting async pipeline for: 'software engineer'
  Workers: 5
  Queue size: 100
  Min score: 50
  Resume: data/resume.txt

[Progress bar and metrics will appear here]

============================================================
Pipeline Complete
============================================================
  Total jobs: 150
  Completed: 142
  Failed: 8
  Time: 45.23s
  Throughput: 3.32 jobs/sec
============================================================
```

## Troubleshooting

### Issue: "AsyncJobPipeline not available"

**Solution:**
```bash
pip install aiosqlite httpx structlog
```

### Issue: High memory usage

**Solution:** Reduce workers and queue size
```bash
python -m src.cli process-async "query" \
  --workers 3 \
  --queue-size 50
```

### Issue: API rate limiting errors

**Solution:** Reduce rate limits
```bash
python -m src.cli process-async "query" \
  --llm-rate 5 \
  --email-rate 1
```

### Issue: Resume file not found

**Solution:** Specify full path
```bash
python -m src.cli process-async "query" \
  --resume /absolute/path/to/resume.txt
```

## Comparison: Sync vs Async Pipeline

### Sync Pipeline (Existing)
```bash
# Slower, uses more memory
python -m src.cli scan "software engineer"
```

### Async Pipeline (New)
```bash
# Faster, constant memory, configurable
python -m src.cli process-async "software engineer"
```

## Next Steps

1. **Start Small:** Test with 10-50 jobs first
2. **Monitor:** Watch memory and CPU usage
3. **Tune:** Adjust workers and queue size based on results
4. **Scale Up:** Gradually increase to larger job volumes
5. **Read Full Guide:** See `docs/async_pipeline_migration.md` for details

## API Response Format

When using the FastAPI endpoint, you'll receive:

```json
{
  "status": "success",
  "trace_id": "abc123",
  "query": "software engineer",
  "jobs_fetched": 150,
  "jobs_processed": 150,
  "jobs_completed": 142,
  "jobs_failed": 8,
  "processing_time_seconds": 45.23,
  "throughput_jobs_per_second": 3.32,
  "resume_used": "data/resume.txt",
  "min_score_requested": 50
}
```

## Support

- **Migration Guide:** `docs/async_pipeline_migration.md`
- **Design Document:** `.kiro/specs/async-job-pipeline-refactor/design.md`
- **Implementation Summary:** `TASK_17_1_IMPLEMENTATION_SUMMARY.md`
