import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useUser, useClerk, useAuth } from "@clerk/react";
import { useLocation } from "react-router-dom";
import { usePersisted, uid } from "../lib/storage.js";
import { DEMO_USER, fromClerkUser } from "../services/authService.js";
import { getPlan } from "../data/plans.js";
import { setTokenGetter } from "../lib/apiClient.js";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

/**
 * App-wide state: user (Clerk or demo), mode, subscription (local until backend), credits, toasts.
 * Mode is derived from the route: /demo/* is demo mode, /app/* is authenticated mode.
 */
export function AppProvider({ children }) {
  const { pathname } = useLocation();
  const { user: clerkUser, isLoaded, isSignedIn } = useUser();
  const { signOut } = useClerk();
  const { getToken } = useAuth();
  // Give the API client access to the Clerk session JWT (used once services call the backend).
  setTokenGetter(getToken);
  const mode = pathname.startsWith("/demo") ? "demo" : "app";
  const user = mode === "demo" ? DEMO_USER : fromClerkUser(clerkUser);

  const [subscription, setSubscription] = usePersisted("subscription", { plan: null, interval: "monthly", status: "none" });
  const [spent, setSpent] = usePersisted("credits:spent", 0);
  const [toasts, setToasts] = useState([]);

  const effectivePlan = mode === "demo" ? getPlan("pro") : subscription.plan ? getPlan(subscription.plan) : null;
  const credits = Math.max(0, (effectivePlan?.credits ?? 0) - spent);

  const toast = useCallback((message, tone = "default") => {
    const id = uid("t");
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);

  const value = useMemo(
    () => ({
      mode,
      base: mode === "demo" ? "/demo" : "/app",
      user,
      authLoaded: mode === "demo" || isLoaded,
      isSignedIn: mode === "demo" || !!isSignedIn,
      signOut: () => signOut({ redirectUrl: "/" }),
      subscription,
      setSubscription,
      plan: effectivePlan,
      credits,
      spendCredits: (n) => setSpent((s) => s + n),
      toasts,
      toast,
      dismissToast: (id) => setToasts((t) => t.filter((x) => x.id !== id)),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, user?.id, isLoaded, isSignedIn, subscription, credits, toasts, toast]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
