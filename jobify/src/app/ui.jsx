import React, { useEffect, useRef } from "react";
import { X, ChevronLeft, ChevronRight, Check, AlertCircle, Inbox } from "lucide-react";
import { cn } from "../lib/utils.js";
import { useApp } from "./AppProvider.jsx";

/* Shared dashboard primitives. Tokens live in styles/globals.css (:root). */

export function Button({ variant = "primary", size = "md", className, type = "button", ...p }) {
  const v = {
    primary: "bg-[#141414] text-white hover:bg-[#2A2A2A]",
    outline: "bg-white text-[#161616] border border-[#E7E7E7] hover:bg-[#F4F4F4]",
    ghost: "text-[#626262] hover:bg-[#F4F4F4] hover:text-[#161616]",
    danger: "bg-[#DC4C5C] text-white hover:bg-[#c43f4e]",
  }[variant];
  const s = { sm: "h-8 px-3 text-[12.5px]", md: "h-9 px-4 text-[13px]", lg: "h-11 px-5 text-[14px]" }[size];
  return (
    <button
      type={type}
      className={cn("inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none active:scale-[0.99]", v, s, className)}
      {...p}
    />
  );
}

export function Badge({ tone = "neutral", className, children }) {
  const t = {
    neutral: "bg-[#F0F0F0] text-[#444]",
    success: "bg-[#E4F6EE] text-[#0E7C57]",
    warning: "bg-[#FDF3DC] text-[#9A6A00]",
    info: "bg-[#E6F0FD] text-[#1B66C0]",
    danger: "bg-[#FCE8EA] text-[#B53545]",
  }[tone];
  return <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap", t, className)}>{children}</span>;
}

export function Avatar({ label, color = "#E9E9E9", fg = "#444", size = 32, square, className }) {
  return (
    <span
      aria-hidden="true"
      style={{ width: size, height: size, background: color, color: fg, fontSize: size * 0.38 }}
      className={cn("shrink-0 inline-flex items-center justify-center font-semibold", square ? "rounded-lg" : "rounded-full", className)}
    >
      {label}
    </span>
  );
}

export const initialsOf = (s = "") => s.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

export function Field({ label, hint, error, children, className, htmlFor }) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={htmlFor} className="text-[12px] text-[#444] font-medium">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p role="alert" className="text-[11.5px] text-[#DC4C5C]">{error}</p>
      ) : hint ? (
        <p className="text-[11.5px] text-[#888]">{hint}</p>
      ) : null}
    </div>
  );
}

export const inputCls =
  "w-full h-10 rounded-lg border border-[#E7E7E7] bg-white px-3 text-[13.5px] text-[#161616] placeholder:text-[#A0A0A0] focus:border-[#161616] focus:outline-none";

export const Input = React.forwardRef(({ className, ...p }, ref) => <input ref={ref} className={cn(inputCls, className)} {...p} />);
export const Textarea = ({ className, ...p }) => <textarea className={cn(inputCls, "h-auto py-2 min-h-[88px] resize-y", className)} {...p} />;
const CHEVRON = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23707070' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`;
export const Select = ({ className, children, style, ...p }) => (
  <select
    style={{ backgroundImage: CHEVRON, backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center", ...style }}
    className={cn(inputCls, "appearance-none pr-8 cursor-pointer", className)}
    {...p}>
    {children}
  </select>
);

/** Accessible modal dialog / side drawer: Escape closes, focus is trapped and restored. */
export function Dialog({ open, onClose, title, children, footer, side, width = 480 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement;
    const el = ref.current;
    el?.querySelector("input,select,textarea,button,[tabindex]")?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && el) {
        const f = [...el.querySelectorAll("a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex='-1'])")];
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus?.(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex" style={{ justifyContent: side ? "flex-end" : "center", alignItems: side ? "stretch" : "center" }}>
      <div className="absolute inset-0 bg-black/30" onClick={onClose} aria-hidden="true" />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{ width: `min(${width}px, 100%)` }}
        className={cn("relative bg-white shadow-xl flex flex-col max-h-full", side ? "h-full" : "rounded-xl max-h-[90vh] mx-4")}
      >
        <div className="flex items-center justify-between px-5 h-14 border-b border-[#E7E7E7] shrink-0">
          <h2 className="text-[15px] font-semibold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="w-8 h-8 rounded-lg hover:bg-[#F4F4F4] flex items-center justify-center">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
        {footer && <div className="px-5 py-3 border-t border-[#E7E7E7] flex justify-end gap-2 shrink-0">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Delete", onConfirm, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} title={title} width={400}
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button></>}>
      <p className="text-[13.5px] text-[#626262]">{message}</p>
    </Dialog>
  );
}

export function Pagination({ page, total, pageSize, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  const btn = "w-8 h-8 rounded-lg flex items-center justify-center text-[13px] hover:bg-[#F0F0F0] disabled:opacity-40 disabled:pointer-events-none";
  return (
    <nav aria-label="Pagination" className="flex items-center gap-1">
      <button type="button" aria-label="Previous page" className={btn} disabled={page === 1} onClick={() => onChange(page - 1)}><ChevronLeft className="w-4 h-4" /></button>
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
        <button key={n} type="button" aria-current={n === page ? "page" : undefined} onClick={() => onChange(n)}
          className={cn(btn, n === page && "bg-[#141414] text-white hover:bg-[#141414]")}>{n}</button>
      ))}
      <button type="button" aria-label="Next page" className={btn} disabled={page === pages} onClick={() => onChange(page + 1)}><ChevronRight className="w-4 h-4" /></button>
    </nav>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6 gap-2">
      <Icon className="w-6 h-6 text-[#A0A0A0]" aria-hidden="true" />
      <p className="text-[14px] font-medium">{title}</p>
      {text && <p className="text-[12.5px] text-[#888] max-w-sm">{text}</p>}
      {action}
    </div>
  );
}

export const Skeleton = ({ className }) => <div className={cn("animate-pulse rounded-md bg-[#EEEEEE]", className)} aria-hidden="true" />;

export function PageHeader({ icon: Icon, title, children, sub }) {
  return (
    <div className="min-h-[52px] border-b border-[#E7E7E7] bg-white px-4 md:px-6 py-2 flex flex-wrap items-center gap-x-3 gap-y-2">
      {Icon && <Icon className="w-4 h-4 text-[#707070]" aria-hidden="true" />}
      <h1 className="text-[14px] font-semibold">{title}</h1>
      {sub}
      <div className="ml-auto flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

export function DemoNotice({ children }) {
  return <p className="text-[11.5px] text-[#888]">{children}</p>;
}

export function ToastViewport() {
  const { toasts, dismissToast } = useApp();
  return (
    <div className="fixed bottom-4 right-4 z-[90] flex flex-col gap-2" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className="flex items-center gap-2 bg-[#141414] text-white text-[13px] rounded-lg pl-3 pr-2 py-2 shadow-lg max-w-sm">
          {t.tone === "error" ? <AlertCircle className="w-4 h-4 text-[#ff8a95]" /> : <Check className="w-4 h-4 text-[#5fe0b0]" />}
          <span className="flex-1">{t.message}</span>
          <button type="button" aria-label="Dismiss" onClick={() => dismissToast(t.id)} className="w-6 h-6 rounded hover:bg-white/10 flex items-center justify-center"><X className="w-3.5 h-3.5" /></button>
        </div>
      ))}
    </div>
  );
}
