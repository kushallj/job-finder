# Frontend-Backend API Integration Guide

## Overview

This document explains the data flow between the frontend and backend, how to debug API issues, and best practices for maintaining synchronization.

## API Architecture

### Core Endpoints

#### 1. **Statistics Endpoint** (`GET /api/stats`)
Returns comprehensive statistics about jobs, contacts, and outreach activities.

**Response Structure:**
```json
{
  "status": "success|error",
  "source": "live|db_fallback|empty",
  "timestamp": "2026-03-14T10:30:00.000000",
  "stats": {
    "total_jobs": number,
    "total_contacts": number,
    "total_applications": number,
    "total_outreach_attempts": number,
    "emails_sent": number,
    "follow_ups_sent": number,
    "success_rate": number (0-100)
  },
  "recent_outreach": [
    {
      "id": number,
      "contact_email": string,
      "status": "sent|bounced|replied|no_response|failed|followed_up",
      "sent_at": "ISO-8601 timestamp"
    }
  ]
}
```

**Data Sources:**
- **live**: Data from `state.outreach_proc.get_stats()` (fastest, real-time)
- **db_fallback**: Data from database queries (fallback when live source unavailable)
- **empty**: Default empty stats when errors occur

---

#### 2. **Contacts Endpoint** (`GET /api/contacts`)
Retrieves paginated contacts with optional company filtering.

**Query Parameters:**
- `page`: number (default: 1)
- `limit`: number (default: 50)
- `company`: string (optional, filters by company name)

**Response Structure:**
```json
{
  "status": "success",
  "contacts": [
    {
      "id": number,
      "name": string,
      "title": string | null,
      "email": string | null,
      "linkedin_url": string | null,
      "company": string,
      "department": string | null,
      "confidence_score": number (0-100),
      "source": "linkedin|website|generated" | null,
      "found_at": "ISO-8601 timestamp"
    }
  ],
  "pagination": {
    "page": number,
    "limit": number,
    "total": number,
    "pages": number
  }
}
```

---

#### 3. **Search Contacts** (`POST /api/contacts/search`)
Searches for and discovers new contacts at a specific company.

**Request Body:**
```json
{
  "company_name": string,
  "job_title": string (optional)
}
```

**Response Structure:**
```json
{
  "status": "success|error",
  "trace_id": "unique-request-id",
  "contacts": [...],
  "total": number
}
```

---

## Data Flow Diagram

```
Frontend Component
    ↓
useStats Hook / useContacts Hook
    ↓
statsApi.getStats() / contactsApi.getAll()
    ↓
Axios Instance (with logging & trace ID)
    ↓
Backend API Endpoint
    ↓
Database Query / Live Processor
    ↓
Response with timestamp & source
    ↓
React Query (caching & retry logic)
    ↓
Component Renders with Data
```

---

## Debugging Guide

### 1. **Check Browser Console for API Logs**

The frontend logs all API requests and responses:

```
[API Request] GET http://localhost:8000/api/stats {
  traceId: "abc123cd",
  params: {...}
}

[API Response] GET http://localhost:8000/api/stats {
  status: 200
}
```

Each request includes a trace ID for matching in backend logs.

### 2. **Check Backend Server Logs**

Monitor these log messages:
```
INFO Stats from live processor: {...}
INFO Stats from DB: jobs=0, contacts=5, apps=2, outreach=1, emails=1, success_rate=100.0%
WARNING Live get_stats() failed, falling back to DB: ...
ERROR Stats endpoint error: ...
```

### 3. **Common Issues & Solutions**

#### Issue: All stats showing as 0

**Possible Causes:**
1. **Empty Database**: No contacts/jobs/outreach records exist
   - **Solution**: Add test data or run job search and contact discovery
   
2. **Live Processor Not Available**: `state.outreach_proc` is None
   - **Check**: Fallback to db_fallback source (check logs for source field)
   - **Solution**: Ensure OutreachProcessor is initialized on backend startup

3. **Database Connection Issue**
   - **Check**: Response status is "error" with error message
   - **Solution**: Verify database connection and migrations are complete

#### Issue: Stats show old values (not updating)

**Possible Causes:**
1. **React Query Stale Time**: Data cached for 5 seconds (stats) or 60 seconds (contacts)
   - **Solution**: Click "Refresh" button or modify staleTime in hooks

2. **New records not hitting database yet**
   - **Check**: Recent outreach timestamps in stats
   - **Solution**: Ensure outreach processor is persisting to database

#### Issue: Contacts list always empty

**Possible Causes:**
1. **Contact search hasn't been run**
   - **Solution**: Use search functionality to discover contacts first

2. **Database doesn't have contacts table or records**
   - **Check**: `/api/contacts` response should show total=0
   - **Solution**: Run contact discovery or import contacts

---

## Frontend Hook Configuration

### useStats Hook
```typescript
{
  stats: OutreachStats,
  recentOutreach: RecentOutreach[],
  isLoadingStats: boolean,
  statsError: Error | null,
  refetchStats: () => void,
  statsSource: "live" | "db_fallback" | "unknown",
  statsTimestamp: string | undefined,
  // ... health API data
}
```

**Automatic Behavior:**
- Fetches on mount
- Retries failed requests 2x with exponential backoff
- Refetches every 30 seconds
- Provides default empty stats if API fails

### useContacts Hook
```typescript
{
  contacts: Contact[],
  pagination: Pagination,
  isLoading: boolean,
  error: Error | null,
  refetch: () => void,
  search: (request: ContactSearchRequest) => void,
  isSearching: boolean,
}
```

**Automatic Behavior:**
- Fetches with page, limit, company filters
- Refetch invalidates stats (for dashboard refresh)
- Retries 2x with exponential backoff
- Caches for 1 minute

---

## Component Usage Examples

### Stats Page
```tsx
export const Stats: React.FC = () => {
  const { stats, statsError, refetchStats, statsSource } = useStats();
  
  // Use stats?.total_jobs, stats?.total_contacts, etc.
  // Show error state if statsError exists
  // Display statsSource in debug info
};
```

### Dashboard Page
```tsx
export const Dashboard: React.FC = () => {
  const { stats, isLoadingStats } = useStats();
  
  // Display stat cards using:
  // - stats?.total_jobs
  // - stats?.total_contacts
  // - stats?.emails_sent
  // - stats?.success_rate
};
```

### Contacts Page
```tsx
export const Contacts: React.FC = () => {
  const { contacts, pagination, isLoading, refetch, search } = useContacts(filters);
  
  // List contacts in table
  // Use pagination for page controls
  // Call search() for company discovery
};
```

---

## Network Request Details

### Headers Added by Frontend
- `X-Trace-ID`: Unique ID per request (for logging correlation)
- `Content-Type`: application/json
- `User-Agent`: Browser default

### Timeout
- 30 seconds per request
- If exceeded, error is logged and promise rejected

### Retry Strategy
- **Stats Hook**: 2 retries with 1000ms, 2000ms delays
- **Contacts Hook**: 2 retries with 1000ms, 2000ms delays
- **Exponential Backoff**: Each retry waits 2x longer than previous

---

## Performance Optimization

### Caching Strategy
| API | Stale Time | Refetch Interval | Use Case |
|-----|-----------|------------------|----------|
| `/api/stats` | 5 seconds | 30 seconds | Fast dashboard updates |
| `/api/contacts` | 60 seconds | N/A | Browse contacts list |
| `/api/health` | 10 seconds | 60 seconds | Subsystem monitoring |

### Best Practices
1. **Don't refetch unnecessarily**: Let React Query handle caching
2. **Use refetch() sparingly**: More than once per 5sec wastes resources
3. **Handle loading/error states**: Always show feedback to user
4. **Log trace IDs**: Match frontend logs with backend logs using X-Trace-ID

---

## Testing the Integration

### 1. Manual Testing
```bash
# Test stats endpoint
curl -i http://localhost:8000/api/stats

# Test contacts endpoint
curl -i "http://localhost:8000/api/contacts?page=1&limit=50"

# Test search endpoint
curl -X POST http://localhost:8000/api/contacts/search \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Google"}'
```

### 2. Browser DevTools Testing
1. Open Network tab
2. Filter by XHR/Fetch
3. Look for:
   - ✅ Green 200 responses
   - ❌ Red 4xx/5xx responses
   - Timing > 2 seconds = slow endpoint

### 3. Console Logging
Enable detailed logging:
```javascript
// In browser console
localStorage.debug = '*'
// Reload page to see enhanced logs
```

---

## Troubleshooting Checklist

- [ ] Backend server running on port 8000?
- [ ] Frontend `.env` has `VITE_API_BASE_URL=http://localhost:8000`?
- [ ] CORS enabled on backend? (should be in FastAPI)
- [ ] Database migrations run? (`migrate_database.py`)
- [ ] Check backend logs for errors?
- [ ] Check browser console for API error messages?
- [ ] Try clicking "Refresh" button on stats page?
- [ ] Try restarting backend server?
- [ ] Try clearing browser cache (Ctrl+Shift+Del)?

---

## Future Improvements

1. ✅ **Real-time Updates**: WebSocket support for live stats
2. ✅ **Bulk Operations**: Multi-select contacts for batch outreach
3. ✅ **Advanced Filtering**: Date ranges, status filters, score thresholds
4. ✅ **Export Features**: CSV, PDF export of stats and contacts
5. ✅ **API Rate Limiting**: Prevent abuse of search endpoints

---

## Contact & Support

For API integration issues:
1. Check this guide first
2. Review backend + frontend logs
3. Verify network connectivity
4. Check database migrations

---

*Last Updated: March 14, 2026*
*Version: 1.0*
