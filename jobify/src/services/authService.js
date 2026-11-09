/**
 * Auth contract. Real authentication is handled by Clerk (@clerk/react, mounted in main.tsx).
 * This module only normalises the Clerk user into Jobify's User shape and defines the
 * DEMO user used by the open /demo/* workspace (which performs no authentication).
 *
 * User:         { id, name, email, avatar?, source: "clerk" | "demo" }
 * Subscription: { plan: "basic" | "pro" | null, interval: "monthly" | "yearly", status: "none" | "demo" | "pending_backend", credits }
 *   Subscription is stored locally until the backend exposes it; frontend flags are NOT authorization.
 */
export const DEMO_USER = {
  id: "demo_user",
  name: "Alex Demo",
  email: "alex@demo.jobify.example",
  avatar: null,
  source: "demo",
};

export const fromClerkUser = (u) =>
  u
    ? {
        id: u.id,
        name: u.fullName || u.primaryEmailAddress?.emailAddress || "Jobify user",
        email: u.primaryEmailAddress?.emailAddress || "",
        avatar: u.imageUrl || null,
        source: "clerk",
      }
    : null;
