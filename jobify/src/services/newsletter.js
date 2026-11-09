import { env } from "../config/env.js";
/**
 * Newsletter subscription service for Jobify
 * 
 * Integration Point:
 * Configure VITE_NEWSLETTER_ENDPOINT in your environment (e.g., Formspree, Mailchimp,
 * Resend, Beehiiv, or a custom Vercel / Cloud Run serverless endpoint).
 * 
 * If no endpoint is configured, this function returns { ok: false, reason: "not-configured" }
 * rather than falsifying subscription success.
 */
export async function subscribeNewsletter(email) {
  const endpoint = env.newsletterEndpoint;

  if (!endpoint || endpoint.trim() === "") {
    return { ok: false, reason: "not-configured" };
  }

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ email }),
    });

    if (response.ok) {
      return { ok: true };
    }

    return {
      ok: false,
      reason: "server-error",
      status: response.status,
    };
  } catch (err) {
    return {
      ok: false,
      reason: "network-error",
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
