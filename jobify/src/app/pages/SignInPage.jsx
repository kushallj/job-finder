import { env } from "../../config/env.js";
import React, { useEffect, useState } from "react";
import { Navigate, useSearchParams, Link } from "react-router-dom";
import { SignIn, SignUp, useUser, useClerk } from "@clerk/react";
import { AlertTriangle } from "lucide-react";
import Logo from "../../components/Logo.jsx";
import { Button } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const HAS_KEY = Boolean(env.clerkPublishableKey);

/** Shown when Clerk can't load: no publishable key in this build, or the script never finished loading. */
function AuthUnavailable({ reason }) {
  return (
    <div role="alert" className="w-full max-w-[400px] rounded-2xl border border-[#E7E7E7] bg-white p-6 text-center shadow-sm">
      <AlertTriangle className="w-6 h-6 mx-auto text-[#EBAA20]" aria-hidden="true" />
      <h2 className="mt-3 text-[16px] font-semibold">Sign-in isn't available right now</h2>
      <p className="mt-2 text-[13px] text-[#626262]">
        {reason === "config"
          ? "This deployment has no authentication key configured. Set VITE_CLERK_PUBLISHABLE_KEY in the hosting environment variables and redeploy."
          : "The authentication service didn't load. Check your connection and try again."}
      </p>
      <div className="mt-4 flex flex-col gap-2">
        {reason !== "config" && <Button onClick={() => window.location.reload()}>Try again</Button>}
        <Link to="/demo/chat" className="inline-flex items-center justify-center h-9 rounded-lg border border-[#E7E7E7] text-[13px] font-medium hover:bg-[#F4F4F4]">Try the demo workspace</Link>
      </div>
    </div>
  );
}

function AuthPanel({ mode, redirect }) {
  const clerk = useClerk();
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    if (clerk.loaded) return;
    const t = setTimeout(() => setTimedOut(true), 8000);
    return () => clearTimeout(t);
  }, [clerk.loaded]);

  if (!clerk.loaded) {
    return timedOut ? <AuthUnavailable reason="load" /> : <p className="text-[13px] text-[#707070]" role="status">Loading sign-in…</p>;
  }
  return mode === "signup" ? (
    <SignUp routing="hash" forceRedirectUrl={redirect} signInUrl="/signin" />
  ) : (
    <SignIn routing="hash" forceRedirectUrl={redirect} signUpForceRedirectUrl={redirect} />
  );
}

/** Split-screen sign-in / sign-up. Authentication itself is Clerk; Google is enabled in the Clerk dashboard. */
export default function SignInPage() {
  const [params, setParams] = useSearchParams();
  const { isLoaded, isSignedIn } = useUser();
  const mode = params.get("mode") === "signup" ? "signup" : "signin";
  const raw = params.get("redirect_to") || "/app/chat";
  const redirect = raw.startsWith("/") && !raw.startsWith("//") ? raw : "/app/chat"; // same-origin paths only

  useEffect(() => { document.title = `${mode === "signup" ? "Sign up" : "Sign in"} · Jobify`; }, [mode]);
  if (isLoaded && isSignedIn) return <Navigate to={redirect} replace />;

  const setMode = (m) => {
    const next = new URLSearchParams(params);
    if (m === "signup") next.set("mode", "signup"); else next.delete("mode");
    setParams(next, { replace: true });
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F5F5F5] font-body">
      <div className="hidden lg:flex relative flex-col justify-between p-10 bg-[#EEEEEE] border-r border-[#E7E7E7] overflow-hidden">
        <Logo variant="nav" />
        <svg aria-hidden="true" viewBox="0 0 400 300" className="absolute right-0 bottom-0 w-[70%] opacity-60" fill="none" stroke="#888" strokeWidth="1">
          {Array.from({ length: 9 }, (_, i) => <path key={i} d={`M${20 + i * 40} 300 Q ${120 + i * 30} ${160 - i * 8} ${400} ${40 + i * 14}`} />)}
        </svg>
        <div className="relative max-w-[460px]">
          <p className="text-[22px] leading-snug">“Bring your jobs, Gmail applications, profile, portfolio, and career assistant into one focused workspace.”</p>
          <p className="mt-3 font-mono text-[12px] text-[#444]">A calmer operating system for your job search</p>
        </div>
      </div>

      <main className="flex flex-col items-center justify-center p-6 gap-5">
        <div className="lg:hidden"><Logo variant="nav" /></div>

        <div role="tablist" aria-label="Account" className="inline-flex rounded-full bg-[#EAEAEA] p-1 text-[13px]">
          {[["signin", "Sign in"], ["signup", "Sign up"]].map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={mode === id} onClick={() => setMode(id)}
              className={cn("h-9 px-5 rounded-full font-medium transition-colors", mode === id ? "bg-[#141414] text-white" : "text-[#444] hover:bg-white")}>{label}</button>
          ))}
        </div>

        {HAS_KEY ? <AuthPanel mode={mode} redirect={redirect} /> : <AuthUnavailable reason="config" />}

        <p className="text-[12px] text-[#707070] text-center max-w-[320px]">
          {mode === "signup" ? "Already have an account? Switch to Sign in above." : "New here? Choose Sign up above, or continue with Google; your account is created automatically."}
        </p>
        <div className="text-[12.5px] text-[#444] flex gap-4">
          <Link to="/demo/chat" className="underline">Try the demo workspace</Link>
          <Link to="/" className="underline">Back to home</Link>
        </div>
      </main>
    </div>
  );
}
