import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useUser, useClerk, useAuth } from "@clerk/react";
import { useLocation } from "react-router-dom";
import { usePersisted, uid } from "../lib/storage.js";
import { DEMO_USER, fromClerkUser } from "../services/authService.js";
import { getPlan } from "../data/plans.js";
import { api, isLive, setLiveMode, setTokenGetter } from "../lib/apiClient.js";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

/**
 * App-wide state: user (Clerk or demo), mode, subscription, credits, toasts.
 * Mode is derived from the route: /demo/* is demo mode, /app/* is authenticated mode.
 * Live (/app + VITE_API_BASE_URL): subscription and credits come from GET /me/subscription and
 * the server decides credit spend, so spendCredits() refetches instead of decrementing locally.
 * Otherwise both stay in localStorage as before.
 */
export function AppProvider({ children }) {
  const { pathname } = useLocation();
  const { user: clerkUser, isLoaded, isSignedIn } = useUser();
  const { signOut } = useClerk();
  const { getToken } = useAuth();
  // Give the API client access to the Clerk session JWT (used once services call the backend).
  setTokenGetter(getToken);
  const mode = pathname.startsWith("/demo") ? "demo" : "app";
  setLiveMode(mode === "app");
  const live = isLive();
  const user = mode === "demo" ? DEMO_USER : fromClerkUser(clerkUser);

  const [serverSub, setServerSub] = useState(null);
  const refreshSubscription = useCallback(() => {
    if (!isLive() || !isSignedIn) return Promise.resolve(null);
    return api("/me/subscription").then((s) => { setServerSub(s); return s; }).catch(() => null);
  }, [isSignedIn]);
  useEffect(() => { if (live && isSignedIn) refreshSubscription(); }, [live, isSignedIn, clerkUser?.id, refreshSubscription]);

  const [subscription, setSubscription] = usePersisted("subscription", { plan: null, interval: "monthly", status: "none" });
  const [spent, setSpent] = usePersisted("credits:spent", 0);
  const [toasts, setToasts] = useState([]);

  const activeSub = live ? (serverSub || { plan: null, interval: "monthly", status: "none", creditsRemaining: 0 }) : subscription;
  const effectivePlan = mode === "demo" ? getPlan("pro") : activeSub.plan ? getPlan(activeSub.plan) : null;
  const credits = live ? activeSub.creditsRemaining ?? 0 : Math.max(0, (effectivePlan?.credits ?? 0) - spent);

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
      subscription: activeSub,
      setSubscription,
      refreshSubscription,
      plan: effectivePlan,
      credits,
      spendCredits: (n) => (live ? refreshSubscription() : setSpent((s) => s + n)),
      toasts,
      toast,
      dismissToast: (id) => setToasts((t) => t.filter((x) => x.id !== id)),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, live, user?.id, isLoaded, isSignedIn, activeSub, credits, toasts, toast, refreshSubscription]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
