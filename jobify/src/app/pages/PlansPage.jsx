import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useUser, useClerk } from "@clerk/react";
import { Check, ArrowLeft, LogOut } from "lucide-react";
import { PLANS, formatMoney, yearlySavings } from "../../data/plans.js";
import { useApp } from "../AppProvider.jsx";
import { Badge, Button } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

/** Plan selection. Plans come from data/plans.js; selection persists locally until the backend owns subscriptions. */
export default function PlansPage() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const { isSignedIn, user: clerkUser } = useUser();
  const { signOut } = useClerk();
  const { subscription, setSubscription } = useApp();
  const [interval, setInterval] = useState(subscription.interval || "monthly");
  const [selected, setSelected] = useState(params.get("plan") === "pro" ? "pro" : subscription.plan || "basic");
  const email = clerkUser?.primaryEmailAddress?.emailAddress;

  useEffect(() => { document.title = "Choose your plan · Jobify"; }, []);

  const proceed = (planId) => {
    setSelected(planId);
    setSubscription({ plan: planId, interval, status: "pending_backend" });
    if (!isSignedIn) nav(`/signin?redirect_to=${encodeURIComponent("/checkout")}`);
    else nav("/checkout");
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] font-body">
      <header className="flex items-center justify-between px-5 h-14">
        <Link to="/" className="inline-flex items-center gap-1.5 text-[13px] text-[#444] hover:text-[#161616]"><ArrowLeft className="w-4 h-4" />Back to home</Link>
        {isSignedIn && <button type="button" onClick={() => signOut({ redirectUrl: "/" })} className="inline-flex items-center gap-1.5 text-[13px] text-[#444]"><LogOut className="w-4 h-4" />Sign out</button>}
      </header>
      <main className="max-w-[780px] mx-auto px-4 pb-16 pt-6 text-center">
        <h1 className="text-[28px] font-semibold font-display">Choose your plan</h1>
        <p className="mt-2 text-[13.5px] text-[#626262]">{email ? <>Billed to {email}. Onboarding unlocks after payment succeeds.</> : "Pick a plan, then sign in to continue."}</p>

        <div className="mt-6 inline-flex items-center gap-3">
          <button type="button" role="switch" aria-checked={interval === "yearly"} aria-label="Bill yearly" onClick={() => setInterval(interval === "yearly" ? "monthly" : "yearly")}
            className={cn("w-9 h-5 rounded-full relative transition-colors", interval === "yearly" ? "bg-[#141414]" : "bg-[#D6D6D6]")}>
            <span className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all", interval === "yearly" ? "left-[18px]" : "left-0.5")} />
          </button>
          <span className="text-[13px]">Bill yearly</span><Badge>2 months free</Badge>
        </div>

        <div className="mt-8 grid md:grid-cols-2 gap-4 text-left items-start">
          {PLANS.map((pl) => {
            const price = interval === "yearly" ? pl.yearly / 12 : pl.monthly;
            return (
              <article key={pl.id} aria-label={`${pl.name} plan`} className={cn("rounded-2xl bg-white border overflow-hidden", selected === pl.id ? "border-[#141414]" : "border-[#E7E7E7]")}>
                {pl.highlight && <div className="bg-[#141414] text-white text-center text-[11px] font-semibold tracking-wide uppercase py-1.5">{pl.highlight}</div>}
                <div className="p-6 border-b border-[#EEE]">
                  <h2 className="text-[15px] font-medium">{pl.name}</h2>
                  <div className="mt-3 flex items-baseline gap-2"><s className="text-[13px] text-[#888]">{formatMoney(pl.listMonthly)}</s><span className="text-[34px] font-semibold leading-none">{formatMoney(price)}</span><Badge>{pl.badge}</Badge><span className="text-[13px] text-[#707070]">/month</span></div>
                  {interval === "yearly" && <p className="mt-2 text-[12px] text-[#13A875]">Billed {formatMoney(pl.yearly)} yearly · save {formatMoney(yearlySavings(pl))}</p>}
                  <p className="mt-2 text-[12.5px] text-[#707070]">{pl.description}</p>
                </div>
                <ul className="p-6 flex flex-col gap-2.5 text-[13px] text-[#444]">
                  {pl.features.map((f) => <li key={f} className="flex gap-2"><Check className="w-4 h-4 mt-0.5 shrink-0" />{f}</li>)}
                  {pl.limits.map((f) => <li key={f} className="flex gap-2 text-[#888]"><span className="w-4 text-center">–</span>{f}</li>)}
                </ul>
                <div className="px-6 pb-6"><Button size="lg" variant={pl.id === "basic" ? "primary" : "outline"} className="w-full" onClick={() => proceed(pl.id)}>{pl.cta}</Button></div>
              </article>
            );
          })}
        </div>
        <p className="mt-6 text-[12px] text-[#888]">Prices shown are demo placeholders. No payment is taken in this build.</p>
      </main>
    </div>
  );
}
