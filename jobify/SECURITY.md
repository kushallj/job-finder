# Security

## Rules for this repo
- No secrets in the frontend. Only `VITE_*` values reach the browser and they are public. `CLERK_SECRET_KEY`, payment keys and AI keys live on the backend only.
- `.env*` files are git-ignored (only `.env.example` is tracked). Rotate any key that was ever pasted in chat or committed.
- Frontend route guards are UX only. The backend must verify the Clerk JWT and authorize every request, filtering data by the authenticated user (never trust a user id sent by the client).
- Prices, discounts, credits and entitlements are computed server-side. Payment is via hosted checkout; the app never handles card data.
- Outreach emails stay preview-and-approve; nothing is sent automatically.
- Security headers are set in `vercel.json`. The CSP ships as `Content-Security-Policy-Report-Only`: load the site, check the browser console for violations (Clerk, fonts, any new third party), then rename the header to `Content-Security-Policy` to enforce it.
- CI runs `npm audit --omit=dev`; keep dependencies updated.

## Reporting a vulnerability
Email the maintainers privately (do not open a public issue).
