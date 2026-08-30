# External Job Intelligence

Job Finder v6 can use two backend-only providers:

- **JobDataAPI**: broad normalized ATS/career-page coverage, salary/remote metadata, freshness and optional semantic/historical data.
- **AI Dev Jobs (AI DevBoard)**: AI-focused job discovery, candidate-profile matching, similar jobs and market statistics.

The providers are accessed only from the backend. API keys are never sent to the frontend.

## Configuration

```env
JOBDATA_API_KEY=
AIDEVBOARD_API_KEY=
PROVIDER_SYNC_LIMIT=50
PROVIDER_SYNC_MAX_AGE_DAYS=30
```

AI Dev Jobs supports public read access for its core search endpoints; a free key can be used for recurring keyed identity/rate-limit handling. JobDataAPI requires an API key for normal access.

## Sync

```http
POST /api/providers/sync
Content-Type: application/json

{
  "query": "backend engineer",
  "location": "India",
  "max_age_days": 30,
  "limit": 50
}
```

Both providers are queried independently. One provider failing does not make the other unavailable. Results are normalized into the existing `jobs` table and deduplicated by provider ID, application URL, or title/company/URL. `provider_sources` preserves cross-provider corroboration.

## Product usage

External provider metadata is surfaced through the existing Opportunity Brief rather than creating a separate provider-centric product. The brief can use:

- salary and currency
- remote/work mode
- normalized experience level
- tags
- provider provenance
- cross-provider corroboration

AI Dev Jobs market statistics are available through:

```http
GET /api/market-intelligence
```

## Design rule

External providers improve retrieval and evidence; **Job Finder remains the decision engine**. Provider scores do not overwrite the application's own fit score. The intended pipeline is:

```text
Provider retrieval
→ local dedup/freshness
→ candidate fit
→ company/contact intelligence
→ Opportunity Score
→ Do This Next
```

## Security

Keep provider keys in backend environment variables only. Do not expose them in browser JavaScript, frontend bundles, URLs, logs, or committed files.
