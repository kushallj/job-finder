# Jobify: Frontend / Backend Integration

The frontend is complete against **local mock services**. Every service lives in `src/services/` and is the single seam to replace with real API calls. Pages never touch `localStorage` or fixtures directly.

All data is demo data. Nothing here sends email, charges money, calls an AI provider, or reads an inbox.

## Routes

| Route | Purpose | Auth |
|---|---|---|
| `/` | Marketing site | public |
| `/signin` (`/login`) | Clerk `<SignIn />` in a split-screen layout. Honors `?redirect_to=` (same-origin paths only) | public |
| `/signup` | Redirects to `/plans` (keeps `?plan=`) | public |
| `/plans` | Plan + billing interval selection | public |
| `/checkout` | Checkout **preview** | Clerk session |
| `/demo/{chat,jobs,applications,founders,portfolio}` | Demo workspace, sample data, fixed demo user | none |
| `/app/{chat,jobs,applications,founders,portfolio}` | Real-user workspace, same components | Clerk session (frontend redirect only) |

Frontend route guards are UX only. **The backend must authorize every request.**

## Authentication (Clerk)

`ClerkProvider` is mounted in `src/main.tsx`. `src/app/AppProvider.jsx` maps the Clerk user to:

```ts
User = { id: string; name: string; email: string; avatar: string | null; source: "clerk" | "demo" }
```

Send the Clerk session token (`getToken()`) as `Authorization: Bearer <jwt>` to the API and verify it server-side. Never trust `user.id` sent from the client. Use `CLERK_SECRET_KEY` only on the server.

## Subscription and entitlements

```ts
Subscription = { plan: "basic" | "pro" | null; interval: "monthly" | "yearly";
                 status: "none" | "pending_backend" | "demo" | "active" | "past_due" | "cancelled";
                 creditsRemaining: number; renewsAt?: string }
```

Today this is stored in `localStorage` (`jobify:subscription`) and credits are a local counter. Replace with `GET /me/subscription`. Plan copy and display prices live in `src/data/plans.js`; real prices and entitlements must come from the backend. Frontend flags are not authorization.

## Contracts (replace the matching service)

Conventions: JSON; success `200` with the body below; errors `{ error: { code, message } }` with 4xx/5xx; lists return `{ items, total, page, pageSize }`. The UI already handles loading, empty and error states.

- **Jobs** (`jobService`): `GET /jobs?q&workModes&types&countries&skills&matchOnly&minSalaryUsd&maxYears&sort&page&pageSize`, `GET /jobs/:id`, `PUT /me/jobs/:id/saved`, `POST /me/jobs/:id/applied`. Job: `{ id, title, company, location, country, experience, salary, skills[], match, workMode: "Remote"|"Hybrid"|"Onsite", type: "Full-time"|"Internship", postedDaysAgo, description, responsibilities[] }`. `match` is computed server-side from the user's profile.
- **Applications** (`applicationService`): `GET /applications`, `POST /applications`, `PATCH /applications/:id`, `DELETE /applications/:id`. Application: `{ id, company, position, stage: "applied"|"interview"|"offer"|"rejected"|"ghosted", subject, sender, date, messages, notes, events[{id,title,at}], offer: {salary,deadline}|null, source }`.
- **Gmail connection** (`applicationService.getConnection/connect/sync/disconnect`): `GET /gmail`, `POST /gmail/connect` (return an OAuth URL; do not fake success), `POST /gmail/sync`, `DELETE /gmail`. State: `{ status: "not_connected"|"pending"|"connected"|"syncing"|"failed"|"disconnected", email, lastSync, nextScan }`. The UI labels the current connection as simulated; remove `simulated` once real.
- **Founders** (`founderService`): `GET /founders?q&country&industry&hiringOnly&page&pageSize`, `PUT /me/founders/:id/saved`, `POST /founders/:id/unlock` (debit credits server-side; return contact fields on success). Company: `{ id, name, website, location, country, industry, description, hiring, founders[{id,name,initials,role,linkedin,x}] }`. Unlock cost is a constant (`UNLOCK_COST`) and must be enforced server-side.
- **Chat** (`chatService`): `GET /conversations`, `POST /conversations`, `PATCH /conversations/:id`, `DELETE /conversations/:id`, `POST /conversations/:id/messages` (`{ content, mode: "ask"|"agent" }`, ideally streamed). The send call accepts an `AbortSignal` for Stop. **Outreach emails must stay preview-and-approve; never send automatically.**
- **Portfolio** (`portfolioService`): `GET /portfolio`, `PUT /portfolio` (draft), `POST /portfolio/publish { username }`, `DELETE /portfolio/publish`, `GET /portfolio/username-available?name=`, `POST /portfolio/regenerate`. Resume parsing and GitHub analysis are not implemented in the frontend. Username rule: 3 to 24 chars `[a-z0-9-]`.
- **Payments** (`CheckoutPage`): the page collects name, email, phone, country, address, business flag, plan, interval, currency, discount code. Handoff: `POST /checkout/session` with those fields, receive a hosted-checkout URL, redirect. Compute prices, discounts and GST on the server. The page never collects card data. Replace the simulated success/failure with the provider's return URLs and webhook-confirmed state.

## Local persistence keys (demo only)

`jobify:{subscription, credits:spent, jobs:state, applications, gmail, founders:state, chats, portfolio}`. Remove once services are API-backed.
