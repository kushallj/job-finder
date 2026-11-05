/**
 * Central plan + entitlement configuration. DEMO VALUES, not confirmed Jobify pricing.
 * Frontend flags are UX hints only; the backend must enforce entitlements.
 */
export const PLANS = [
  {
    id: "basic",
    name: "Basic",
    description: "Everything you need to run a focused job search.",
    monthly: 5,
    yearly: 50,
    listMonthly: 10,
    badge: "50% off",
    highlight: null,
    credits: 500,
    features: [
      "Browse startup jobs (demo catalogue)",
      "500 AI credits every month",
      "Application tracking from Gmail (simulated)",
      "Resume and portfolio builder",
      "Portfolio chatbot",
      "Cold email drafts to startup founders",
    ],
    limits: ["No HR outreach at large companies"],
    cta: "Continue with Basic",
  },
  {
    id: "pro",
    name: "Pro",
    description: "More credits and wider outreach.",
    monthly: 8,
    yearly: 80,
    listMonthly: 20,
    badge: "60% off",
    highlight: "Limited offer",
    credits: 1500,
    features: ["Everything in Basic, plus", "1,500 AI credits every month", "Outreach to HR teams at larger companies"],
    limits: [],
    cta: "Continue with Pro",
  },
];

export const getPlan = (id) => PLANS.find((p) => p.id === id) || PLANS[0];

export const CURRENCIES = {
  USD: { rate: 1, locale: "en-US" },
  INR: { rate: 83, locale: "en-IN" },
};

export const formatMoney = (usd, currency = "USD") => {
  const v = usd * CURRENCIES[currency].rate;
  return new Intl.NumberFormat(CURRENCIES[currency].locale, {
    style: "currency",
    currency,
    minimumFractionDigits: Number.isInteger(v) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(v);
};

export const yearlySavings = (plan) => plan.monthly * 12 - plan.yearly;

/** Demo discount codes (frontend simulation only). */
export const DISCOUNT_CODES = { WELCOME10: 0.1, STUDENT20: 0.2 };
export const GST_RATE = 0.18;
