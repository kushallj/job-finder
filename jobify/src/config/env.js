/**
 * Single place that reads build-time environment variables.
 * Only VITE_* values are exposed to the browser: never put secrets here.
 */
const trimSlash = (s = "") => s.replace(/\/+$/, "");

export const env = Object.freeze({
  clerkPublishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "",
  apiBaseUrl: trimSlash(import.meta.env.VITE_API_BASE_URL || ""),
  newsletterEndpoint: import.meta.env.VITE_NEWSLETTER_ENDPOINT || "",
  supportEmail: import.meta.env.VITE_SUPPORT_EMAIL || "",
  isProd: import.meta.env.PROD,
});

/** True when a backend is configured. Services use mocks when this is false. */
export const hasApi = Boolean(env.apiBaseUrl);
