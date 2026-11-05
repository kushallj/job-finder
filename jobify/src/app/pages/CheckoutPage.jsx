import React, { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useUser } from "@clerk/react";
import { ArrowLeft, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { CURRENCIES, DISCOUNT_CODES, GST_RATE, formatMoney, getPlan } from "../../data/plans.js";
import { useApp } from "../AppProvider.jsx";
import { Button, Field, Input, Select } from "../ui.jsx";

const COUNTRIES = ["India", "United States", "United Kingdom", "Germany", "Singapore", "Canada", "Australia"];

/**
 * Checkout PREVIEW. No payment provider is connected and no card data is collected.
 * Backend handoff: POST the order summary below, receive a hosted-checkout URL, redirect.
 */
export default function CheckoutPage() {
  const nav = useNavigate();
  const { isLoaded, isSignedIn, user } = useUser();
  const { subscription, setSubscription, toast } = useApp();
  const plan = getPlan(subscription.plan || "basic");
  const yearly = subscription.interval === "yearly";
  const [currency, setCurrency] = useState("INR");
  const [code, setCode] = useState("");
  const [applied, setApplied] = useState(null);
  const [codeErr, setCodeErr] = useState("");
  const [form, setForm] = useState({ name: "", email: "", phone: "", country: "India", address: "", business: false });
  const [errors, setErrors] = useState({});
  const [state, setState] = useState("form"); // form | processing | success | failed | cancelled

  useEffect(() => {
    if (user) setForm((f) => ({ ...f, name: f.name || user.fullName || "", email: f.email || user.primaryEmailAddress?.emailAddress || "" }));
  }, [user]);
  useEffect(() => { document.title = "Checkout · Jobify"; }, []);

  const totals = useMemo(() => {
    const subtotal = yearly ? plan.yearly : plan.monthly;
    const list = yearly ? plan.listMonthly * 12 : plan.listMonthly;
    const planDiscount = list - subtotal;
    const codeDiscount = applied ? subtotal * DISCOUNT_CODES[applied] : 0;
    const taxable = subtotal - codeDiscount;
    const gst = form.country === "India" ? taxable * GST_RATE : 0;
    return { list, planDiscount, codeDiscount, gst, total: taxable + gst };
  }, [plan, yearly, applied, form.country]);

  if (isLoaded && !isSignedIn) return <Navigate to="/signin?redirect_to=%2Fcheckout" replace />;
  if (!subscription.plan) return <Navigate to="/plans" replace />;

  const applyCode = () => {
    const c = code.trim().toUpperCase();
    if (DISCOUNT_CODES[c]) { setApplied(c); setCodeErr(""); toast(`Code ${c} applied (demo).`); } else { setApplied(null); setCodeErr("That code isn't valid."); }
  };

  const validate = () => {
    const e = {};
    if (form.name.trim().length < 2) e.name = "Enter your full name";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Enter a valid email";
    if (form.phone && !/^\+?[\d\s-]{7,15}$/.test(form.phone)) e.phone = "Enter a valid phone number";
    if (form.address.trim().length < 5) e.address = "Enter your billing address";
    setErrors(e);
    return !Object.keys(e).length;
  };

  const pay = async (outcome) => {
    if (!validate()) return;
    setState("processing");
    await new Promise((r) => setTimeout(r, 1400));
    if (outcome === "fail") return setState("failed");
    setSubscription({ plan: plan.id, interval: subscription.interval, status: "demo" });
    setState("success");
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  if (state === "success" || state === "failed" || state === "cancelled") {
    const ok = state === "success";
    return (
      <div className="min-h-screen flex items-center justify-center bg-white p-6 font-body">
        <div className="max-w-[420px] text-center flex flex-col items-center gap-3">
          {ok ? <CheckCircle2 className="w-10 h-10 text-[#13A875]" /> : <XCircle className="w-10 h-10 text-[#DC4C5C]" />}
          <h1 className="text-[20px] font-semibold">{ok ? "Simulated payment complete" : state === "failed" ? "Simulated payment failed" : "Checkout cancelled"}</h1>
          <p className="text-[13px] text-[#626262]">{ok ? "No money was charged and no payment provider was contacted. When the backend is connected, this screen will follow a real payment confirmation." : "Nothing was charged. You can try again or change your plan."}</p>
          <div className="flex gap-2 mt-2">
            {ok ? <Button onClick={() => nav("/app/chat")}>Continue to Jobify</Button> : <Button onClick={() => setState("form")}>Back to checkout</Button>}
            {!ok && <Button variant="outline" onClick={() => nav("/plans")}>Change plan</Button>}
          </div>
        </div>
      </div>
    );
  }

  const row = "flex justify-between text-[13px]";
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white font-body">
      <section className="px-6 lg:px-16 py-8 lg:py-12" aria-label="Order summary">
        <div className="max-w-[512px] ml-auto">
          <div className="flex items-center justify-between">
            <Link to="/plans" aria-label="Back to plans" className="flex items-center gap-3"><ArrowLeft className="w-4 h-4" /><span className="font-display font-semibold">Jobify</span></Link>
            <label className="sr-only" htmlFor="cur">Currency</label>
            <Select id="cur" value={currency} onChange={(e) => setCurrency(e.target.value)} className="w-[130px] h-9 text-[12.5px]">{Object.keys(CURRENCIES).map((c) => <option key={c} value={c}>Pay in {c}</option>)}</Select>
          </div>
          <div className="mt-10 flex justify-between items-baseline"><h1 className="text-[15px] font-semibold">Jobify {plan.name} <span className="text-[#888] font-normal">({yearly ? "yearly" : "monthly"})</span></h1>
            <div><s className="text-[12px] text-[#888] mr-1.5">{formatMoney(plan.listMonthly, currency)}</s><span className="text-[15px] font-semibold">{formatMoney(yearly ? plan.yearly / 12 : plan.monthly, currency)}</span><span className="text-[12px] text-[#888]">/mo</span></div></div>
          <ul className="mt-3 text-[13px] text-[#626262] list-disc pl-5 space-y-1">{plan.features.slice(0, 3).map((f) => <li key={f}>{f}</li>)}</ul>
          <div className="mt-6 rounded-xl border border-[#E7E7E7] p-3">
            <div className="flex items-center gap-2"><label htmlFor="code" className="sr-only">Discount code</label>
              <Input id="code" placeholder="Have a discount code?" value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={(e) => e.key === "Enter" && applyCode()} className="border-0 h-9" />
              <Button variant="outline" size="sm" onClick={applyCode}>Apply</Button></div>
            {codeErr && <p role="alert" className="text-[11.5px] text-[#DC4C5C] px-1 pt-1">{codeErr}</p>}
            {applied && <p className="text-[11.5px] text-[#13A875] px-1 pt-1">{applied} applied. Try WELCOME10 or STUDENT20 (demo codes).</p>}
          </div>
          <div className="mt-6 flex flex-col gap-3">
            <div className={row}><span className="text-[#626262]">Subtotal</span><span>{formatMoney(totals.list, currency)}</span></div>
            <div className={row}><span className="text-[#626262]">Discount</span><span>-{formatMoney(totals.planDiscount + totals.codeDiscount, currency)}</span></div>
            <div className={row}><span className="text-[#626262]">GST ({form.country === "India" ? "18%" : "n/a"})</span><span>{formatMoney(totals.gst, currency)}</span></div>
            <div className="flex justify-between border-t border-[#E7E7E7] pt-4 text-[15px] font-semibold"><span>Total</span><span>{formatMoney(totals.total, currency)}</span></div>
            <p className="text-[11.5px] text-[#888]">Preview only: figures are estimates and no payment provider is connected.</p>
          </div>
        </div>
      </section>

      <section className="px-6 lg:px-16 py-8 lg:py-12 bg-[#FAFAFA] lg:border-l border-[#E7E7E7]" aria-label="Billing details">
        <form noValidate onSubmit={(e) => { e.preventDefault(); pay("success"); }} className="max-w-[512px] flex flex-col gap-4">
          <h2 className="text-[15px] font-semibold">Contact information</h2>
          <Field label="Full name *" htmlFor="cn" error={errors.name}><Input id="cn" autoComplete="name" value={form.name} onChange={set("name")} /></Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Email *" htmlFor="ce" error={errors.email}><Input id="ce" type="email" autoComplete="email" value={form.email} onChange={set("email")} /></Field>
            <Field label="Phone (optional)" htmlFor="cp" error={errors.phone}><Input id="cp" type="tel" autoComplete="tel" placeholder="+91" value={form.phone} onChange={set("phone")} /></Field>
          </div>
          <h2 className="text-[15px] font-semibold pt-2">Billing address *</h2>
          <Field label="Country" htmlFor="cc"><Select id="cc" value={form.country} onChange={set("country")}>{COUNTRIES.map((c) => <option key={c}>{c}</option>)}</Select></Field>
          <Field label="Address" htmlFor="ca" error={errors.address}><Input id="ca" autoComplete="street-address" placeholder="Street, city, postal code" value={form.address} onChange={set("address")} /></Field>
          <label className="flex items-center gap-2 text-[13px]"><input type="checkbox" checked={form.business} onChange={set("business")} />Purchasing as a business</label>
          <Button type="submit" size="lg" disabled={state === "processing"}>{state === "processing" ? <><Loader2 className="w-4 h-4 animate-spin" />Processing…</> : "Continue to Payment"}</Button>
          <div className="flex gap-2 text-[12px]">
            <button type="button" className="underline text-[#626262]" onClick={() => pay("fail")}>Simulate failure</button>
            <button type="button" className="underline text-[#626262]" onClick={() => setState("cancelled")}>Cancel checkout</button>
          </div>
          <p className="text-[11.5px] text-[#888]">Simulated checkout. Do not enter card details; none are requested or stored.</p>
        </form>
      </section>
    </div>
  );
}
