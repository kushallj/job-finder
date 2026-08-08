# Health Check API Documentation

## Overview

The NEXUS system provides a comprehensive health check endpoint at `/api/health` that verifies the operational status of all system components. This endpoint is essential for monitoring, alerting, and ensuring system reliability in production environments.

## Endpoint Details

### GET /api/health

**Description:** Returns detailed health status for all system components including internal services, external APIs, and infrastructure.

**Requirements Satisfied:**
- Requirement 23.6: Health check endpoints
- Requirement 22.1: Ollama integration health check
- Requirement 22.2: Database connectivity check
- Requirement 22.3: Email service (SMTP) connectivity check
- Requirement 22.4: GitHub API status check
- Requirement 22.5: Cloudflare API status check
- Requirement 22.6: Google Sheets API status check

**Authentication:** None required (public endpoint for monitoring)

**Response Status Codes:**
- `200 OK`: Health check completed (check `status` field for actual health)

## Response Structure

```json
{
  "status": "healthy|healthy_with_warnings|degraded|unhealthy",
  "timestamp": "2024-03-15T10:30:00.000Z",
  "version": "2.1.0",
  "components": {
    "ollama": { ... },
    "database": { ... },
    "email": { ... },
    "github": { ... },
    "cloudflare": { ... },
    "google_sheets": { ... },
    "internal_services": { ... }
  },
  "summary": {
    "total_components": 7,
    "healthy_components": 6,
    "health_percentage": 85.7
  },
  "issues": [ ... ],
  "warnings": [ ... ]
}
```

## Overall Status Values

| Status | Description | Action Required |
|--------|-------------|-----------------|
| `healthy` | All critical services operational | None |
| `healthy_with_warnings` | Core services operational, optional services have warnings | Review warnings |
| `degraded` | Some services unavailable but system functional | Investigate issues |
| `unhealthy` | Critical services down | Immediate action required |

## Component Health Checks

### 1. Ollama (Local LLM)

**Requirement:** 22.1 - Integrate with Ollama for local LLM processing

Verifies:
- Ollama service is running at `http://localhost:11434`
- At least one supported model is installed
- Model availability for LLM operations

**Response Structure:**
```json
{
  "ollama": {
    "status": "healthy|unavailable|error",
    "model": "qwen2.5-coder:7b",
    "url": "http://localhost:11434",
    "message": "Ollama running with model qwen2.5-coder:7b"
  }
}
```

**Status Values:**
- `healthy`: Ollama running with a supported model
- `unavailable`: Ollama not running or no models installed
- `error`: Health check failed with exception

**Troubleshooting:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Install recommended model
ollama pull qwen2.5-coder:7b

# Restart Ollama
ollama serve
```

### 2. Database (SQLite)

**Requirement:** 22.1 - Check database connectivity and table status

Verifies:
- Database connection is active
- All required tables exist (jobs, applications, contacts, outreach_records)
- Processing results table exists (for async pipeline)
- Row counts for monitoring

**Response Structure:**
```json
{
  "database": {
    "status": "healthy|error",
    "type": "SQLite",
    "tables": {
      "jobs": 1278,
      "applications": 856,
      "contacts": 120,
      "outreach_records": 125,
      "processing_results": 450
    },
    "message": "Database healthy with 1278 jobs indexed"
  }
}
```

**Status Values:**
- `healthy`: Database accessible, all tables present
- `error`: Connection failed or query error

**Troubleshooting:**
```bash
# Check database file exists
ls -lh job_automation.db

# Verify database schema
sqlite3 job_automation.db ".schema"

# Check database integrity
sqlite3 job_automation.db "PRAGMA integrity_check;"
```

### 3. Email Service (SMTP)

**Requirement:** 22.3 - Integrate with Gmail SMTP for email sending

Verifies:
- SMTP connection is configured and working
- Google Sheets integration (optional)
- Resume PDF availability
- AI service for email generation

**Response Structure:**
```json
{
  "email": {
    "status": "healthy|degraded|unavailable|error",
    "provider": "smtp",
    "smtp": {
      "status": "healthy|unavailable",
      "details": "Connected to smtp.gmail.com:587"
    },
    "google_sheets": {
      "status": "healthy|not_configured",
      "details": "OK"
    },
    "resume_pdf": {
      "status": "healthy|missing",
      "details": "Found at data/resume.pdf"
    },
    "ai_service": {
      "status": "healthy|unavailable",
      "details": "OK"
    },
    "message": "Email service using smtp"
  }
}
```

**Status Values:**
- `healthy`: All email components operational
- `degraded`: SMTP works but optional components unavailable
- `unavailable`: Email service not initialized
- `error`: Health check failed

**Troubleshooting:**
```bash
# Verify SMTP credentials in .env
grep GMAIL_ .env

# Test SMTP connection
python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.login('your-email@gmail.com', 'your-app-password')
print('SMTP OK')
"
```

### 4. GitHub API

**Requirement:** 22.4 - Integrate with GitHub API for commit email mining

Verifies:
- GitHub API credentials are valid
- Rate limit status
- API connectivity

**Response Structure:**
```json
{
  "github": {
    "status": "healthy|rate_limited|not_configured|timeout|error",
    "rate_limit": {
      "remaining": 4850,
      "limit": 5000,
      "percentage": 97.0
    },
    "message": "GitHub API healthy with 4850/5000 requests remaining"
  }
}
```

**Status Values:**
- `healthy`: API accessible with sufficient rate limit
- `rate_limited`: API accessible but low rate limit (<100 remaining)
- `not_configured`: GITHUB_TOKEN not set
- `timeout`: API request timed out
- `error`: API returned error status

**Troubleshooting:**
```bash
# Check GitHub token
grep GITHUB_TOKEN .env

# Test GitHub API
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit

# Check rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit | jq .rate
```

### 5. Cloudflare API

**Requirement:** 22.5 - Integrate with Cloudflare for browser rendering

Verifies:
- Cloudflare account credentials are valid
- Account is accessible
- Browser rendering API available

**Response Structure:**
```json
{
  "cloudflare": {
    "status": "healthy|not_configured|timeout|error",
    "account_id": "abc12345...",
    "message": "Cloudflare browser rendering available"
  }
}
```

**Status Values:**
- `healthy`: Cloudflare API accessible
- `not_configured`: Credentials not set
- `timeout`: API request timed out
- `error`: Authentication failed

**Troubleshooting:**
```bash
# Check Cloudflare credentials
grep CLOUDFLARE_ .env

# Test Cloudflare API
curl -X GET "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### 6. Google Sheets API

**Requirement:** 22.6 - Integrate with Google Sheets API for data export

Verifies:
- Service account credentials file exists
- Credentials are valid JSON
- Credentials are service account type
- Sheet ID is configured

**Response Structure:**
```json
{
  "google_sheets": {
    "status": "configured|not_configured|misconfigured|error",
    "sheet_id": "1A2B3C4D5E6F7G8H9I0J...",
    "credentials": "valid_service_account",
    "message": "Google Sheets export configured"
  }
}
```

**Status Values:**
- `configured`: Credentials valid and ready
- `not_configured`: Missing GOOGLE_SHEET_ID or credentials file
- `misconfigured`: Invalid credentials format
- `error`: Credentials check failed

**Troubleshooting:**
```bash
# Check Google Sheets configuration
grep GOOGLE_ .env
ls -lh $(grep GOOGLE_CREDENTIALS_PATH .env | cut -d= -f2)

# Validate credentials JSON
cat credentials.json | jq .type
# Should output: "service_account"
```

### 7. Internal Services

Verifies:
- JobProcessor initialization
- OutreachProcessor availability
- AsyncJobPipeline availability
- ContactFinder module availability
- EmailDiscovery module availability

**Response Structure:**
```json
{
  "internal_services": {
    "job_processor": {
      "status": "healthy|unavailable",
      "description": "Core job processing service"
    },
    "outreach_processor": {
      "status": "healthy|unavailable",
      "description": "Production outreach orchestrator"
    },
    "async_pipeline": {
      "status": "healthy|unavailable",
      "description": "High-performance async job processing"
    },
    "contact_finder": {
      "status": "available|unavailable",
      "description": "Contact discovery service"
    },
    "email_discovery": {
      "status": "available|unavailable",
      "description": "Multi-provider email discovery"
    }
  }
}
```

## Summary Section

The summary provides a high-level overview of system health:

```json
{
  "summary": {
    "total_components": 7,
    "healthy_components": 6,
    "health_percentage": 85.7
  }
}
```

- `total_components`: Number of checked components
- `healthy_components`: Count of components with healthy/configured/available status
- `health_percentage`: Percentage of healthy components

## Issues and Warnings

### Issues Array

Critical problems that require attention:
```json
{
  "issues": [
    "Ollama not running or no models available - run: ollama pull mistral:latest",
    "Database check failed: connection timeout",
    "Email SMTP connection not available - check GMAIL_ADDRESS and GMAIL_PASSWORD"
  ]
}
```

When issues are present, overall status becomes `degraded`.

### Warnings Array

Non-critical warnings about optional services:
```json
{
  "warnings": [
    "GitHub API not configured - set GITHUB_TOKEN for email discovery",
    "Google Sheets not configured - campaign tracking using local storage",
    "Cloudflare not configured - set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN"
  ]
}
```

Warnings appear when optional services are unconfigured but don't affect core functionality.

## Usage Examples

### Basic Health Check

```bash
curl -X GET http://localhost:8000/api/health | jq .
```

### Check Specific Component

```bash
# Check Ollama status
curl -s http://localhost:8000/api/health | jq '.components.ollama'

# Check database status
curl -s http://localhost:8000/api/health | jq '.components.database'

# Check email service
curl -s http://localhost:8000/api/health | jq '.components.email'
```

### Monitor Overall Health

```bash
# Get overall status
curl -s http://localhost:8000/api/health | jq '.status'

# Get health percentage
curl -s http://localhost:8000/api/health | jq '.summary.health_percentage'

# List all issues
curl -s http://localhost:8000/api/health | jq '.issues[]?'
```

### Integration with Monitoring Tools

#### Prometheus

```python
from prometheus_client import Gauge

health_gauge = Gauge('nexus_health_percentage', 'Overall system health percentage')

async def update_health_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/health")
        data = response.json()
        health_gauge.set(data["summary"]["health_percentage"])
```

#### Shell Script for Monitoring

```bash
#!/bin/bash
# monitor_health.sh - Simple health monitoring script

HEALTH_URL="http://localhost:8000/api/health"
ALERT_THRESHOLD=70

while true; do
    HEALTH=$(curl -s $HEALTH_URL | jq '.summary.health_percentage')
    STATUS=$(curl -s $HEALTH_URL | jq -r '.status')
    
    echo "$(date): Health: $HEALTH%, Status: $STATUS"
    
    if (( $(echo "$HEALTH < $ALERT_THRESHOLD" | bc -l) )); then
        echo "⚠️  ALERT: Health below threshold!"
        curl -s $HEALTH_URL | jq '.issues[]?'
    fi
    
    sleep 60
done
```

#### Python Health Monitoring

```python
import asyncio
import httpx
from datetime import datetime

async def monitor_health():
    """Continuous health monitoring with alerts."""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get("http://localhost:8000/api/health", timeout=5.0)
                data = response.json()
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status = data["status"]
                health_pct = data["summary"]["health_percentage"]
                
                print(f"[{timestamp}] Status: {status}, Health: {health_pct}%")
                
                if status == "degraded":
                    print("⚠️  ISSUES DETECTED:")
                    for issue in data.get("issues", []):
                        print(f"  - {issue}")
                
                if data.get("warnings"):
                    print("ℹ️  WARNINGS:")
                    for warning in data.get("warnings", []):
                        print(f"  - {warning}")
                        
            except Exception as e:
                print(f"[{timestamp}] ❌ Health check failed: {e}")
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor_health())
```

## Testing

### Unit Tests

Run health check tests:
```bash
pytest tests/test_health_check.py -v
```

### Test Coverage

The test suite covers:
- ✅ All services healthy scenario
- ✅ Ollama unavailable scenario
- ✅ Database error scenario
- ✅ Email service unavailable scenario
- ✅ GitHub API error scenario
- ✅ Services not configured scenario
- ✅ Response structure validation
- ✅ Root endpoint health check

### Manual Testing

```bash
# Test with all services available
curl http://localhost:8000/api/health | jq '.status'

# Stop Ollama and test
pkill ollama
curl http://localhost:8000/api/health | jq '.components.ollama.status'

# Test with missing credentials
mv .env .env.bak
curl http://localhost:8000/api/health | jq '.warnings'
```

## Best Practices

### 1. Regular Monitoring

- Set up automated health checks every 60 seconds
- Alert on `degraded` status
- Track health percentage trends over time

### 2. Graceful Degradation

The system is designed to continue functioning even when optional services are unavailable:

- **Ollama down** → Falls back to Gemini API or keyword matching
- **GitHub API unavailable** → Uses other email discovery methods
- **Google Sheets unavailable** → Uses local JSON storage
- **Cloudflare unavailable** → Uses direct HTTP scraping

### 3. Production Deployment

```yaml
# docker-compose.yml health check example
services:
  nexus:
    image: nexus:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 4. Kubernetes Probes

```yaml
# Kubernetes deployment with health checks
apiVersion: v1
kind: Pod
metadata:
  name: nexus
spec:
  containers:
  - name: nexus
    image: nexus:latest
    livenessProbe:
      httpGet:
        path: /api/health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /api/health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
```

## Troubleshooting Guide

### Issue: Overall status is "degraded"

1. Check the `issues` array for specific problems
2. Investigate each failing component
3. Verify environment variables in `.env`
4. Check service logs in `logs/main.log`

### Issue: Ollama shows "unavailable"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Install model
ollama pull qwen2.5-coder:7b
```

### Issue: Database shows "error"

```bash
# Check database file
ls -lh job_automation.db

# Check database integrity
sqlite3 job_automation.db "PRAGMA integrity_check;"

# Recreate database if corrupted
python -c "from src.database import init_db; init_db()"
```

### Issue: Email shows "unavailable"

```bash
# Check SMTP credentials
grep GMAIL_ .env

# Test SMTP manually
python tests/test_smtp_connection.py

# Verify app password (not regular password)
# Generate at: https://myaccount.google.com/apppasswords
```

### Issue: High response time

If health checks take too long:
1. Check network connectivity to external APIs
2. Increase timeout values in health check code
3. Consider caching health check results
4. Verify database query performance

## Security Considerations

### 1. Sensitive Data

The health check endpoint does NOT expose:
- Full API keys (only masked versions)
- Email passwords
- Service account private keys
- Database connection strings

### 2. Public Exposure

The `/api/health` endpoint is intentionally public for monitoring tools. If you need to restrict access:

```python
from fastapi import Header, HTTPException

@app.get("/api/health")
async def health(x_monitoring_token: str = Header(None)):
    if x_monitoring_token != os.getenv("MONITORING_TOKEN"):
        raise HTTPException(401, "Unauthorized")
    # ... rest of health check
```

### 3. Rate Limiting

Consider rate limiting health checks to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/health")
@limiter.limit("60/minute")
async def health():
    # ... health check logic
```

## Performance Considerations

- **Response Time**: Typically 200-500ms with all services healthy
- **Timeout**: Each external API check has a 5-second timeout
- **Caching**: Consider caching health status for 30-60 seconds in high-traffic scenarios
- **Parallel Checks**: External API checks run sequentially; could be parallelized for better performance

## Future Enhancements

Planned improvements:
- [ ] Parallel component health checks for faster response
- [ ] Health check result caching with configurable TTL
- [ ] Detailed metrics per component (latency, error rates)
- [ ] Historical health data storage and trends
- [ ] Webhook alerts on status changes
- [ ] Health check dashboard UI
- [ ] Per-component enable/disable configuration

## Related Documentation

- [API Documentation](./API_DOCUMENTATION.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Monitoring and Observability](./MONITORING.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

## Support

For issues or questions:
1. Check this documentation
2. Review logs in `logs/main.log`
3. Run tests: `pytest tests/test_health_check.py -v`
4. Check GitHub issues
5. Contact system administrators

---

**Last Updated:** 2024-03-15  
**Version:** 2.1.0  
**Status:** Production Ready ✅
