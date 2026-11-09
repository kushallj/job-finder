import React, { Suspense, useEffect, useRef, useState } from "react";
import { NavLink, Navigate, Outlet, Link, useLocation } from "react-router-dom";
import { MessageCircle, Briefcase, LayoutPanelTop, Users, AppWindow, PanelLeft, Menu, ChevronsUpDown, LogOut, CreditCard, ArrowLeftRight } from "lucide-react";
import { useApp } from "./AppProvider.jsx";
import { Avatar, Skeleton, ToastViewport, initialsOf } from "./ui.jsx";
import { cn } from "../lib/utils.js";
import Logo from "../components/Logo.jsx";

const CAREER = [
  { to: "chat", label: "New Chat", icon: MessageCircle },
  { to: "jobs", label: "Jobs", icon: Briefcase },
  { to: "applications", label: "Applications", icon: LayoutPanelTop },
  { to: "founders", label: "Founders", icon: Users },
];
const TOOLS = [{ to: "portfolio", label: "Portfolio", icon: AppWindow }];

function Brand({ collapsed }) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <Logo variant="nav" showWordmark={!collapsed} />
      {!collapsed && <span className="text-[11px] text-[#707070] border border-[#E7E7E7] rounded-full px-1.5 py-0.5">Dashboard</span>}
    </div>
  );
}

function NavItem({ item, base, collapsed, onNavigate }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={`${base}/${item.to}`}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn("flex items-center gap-2.5 h-8 px-2.5 rounded-lg text-[13px] transition-colors", isActive ? "bg-[#EDEDED] text-[#161616] font-medium" : "text-[#444] hover:bg-[#F0F0F0]", collapsed && "justify-center px-0")
      }
    >
      <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
      {!collapsed && item.label}
    </NavLink>
  );
}

function ProfileMenu({ collapsed }) {
  const { user, mode, signOut, plan, credits } = useApp();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = (e) => { if (e.type === "keydown" ? e.key === "Escape" : !ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);
  const item = "flex items-center gap-2 w-full px-3 h-9 text-[13px] text-left hover:bg-[#F4F4F4]";
  return (
    <div ref={ref} className="relative p-2 border-t border-[#E7E7E7]">
      {open && (
        <div role="menu" className="absolute bottom-full left-2 right-2 mb-1 bg-white border border-[#E7E7E7] rounded-xl shadow-lg py-1 z-10 min-w-[200px]">
          <div className="px-3 py-2 text-[12px] text-[#707070] border-b border-[#F0F0F0]">
            {mode === "demo" ? "Demo account" : plan ? `${plan.name} plan` : "No plan"} · {credits} credits
          </div>
          {mode === "demo" ? (
            <>
              <Link role="menuitem" to="/app/chat" className={item}><ArrowLeftRight className="w-4 h-4" />Switch to my account</Link>
              <Link role="menuitem" to="/signup" className={item}><CreditCard className="w-4 h-4" />Choose a plan</Link>
            </>
          ) : (
            <>
              <Link role="menuitem" to="/plans" className={item}><CreditCard className="w-4 h-4" />Subscription</Link>
              <Link role="menuitem" to="/demo/chat" className={item}><ArrowLeftRight className="w-4 h-4" />Open demo workspace</Link>
              <button role="menuitem" type="button" onClick={signOut} className={item}><LogOut className="w-4 h-4" />Sign out</button>
            </>
          )}
        </div>
      )}
      <button type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}
        className={cn("w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#F0F0F0] text-left", collapsed && "justify-center")}>
        {user?.avatar ? <img src={user.avatar} alt="" width={32} height={32} className="w-8 h-8 rounded-lg" /> : <Avatar label={initialsOf(user?.name)} square />}
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1 leading-tight">
              <span className="block text-[13px] font-medium truncate">{user?.name}</span>
              <span className="block text-[11.5px] text-[#707070] truncate">{user?.email}</span>
            </span>
            <ChevronsUpDown className="w-4 h-4 text-[#707070]" aria-hidden="true" />
          </>
        )}
      </button>
    </div>
  );
}

function SidebarBody({ collapsed, onToggle, base, onNavigate, showToggle = true }) {
  return (
    <div className="flex flex-col h-full">
      <div className={cn("flex items-center h-[64px] px-3 shrink-0", collapsed ? "justify-center" : "justify-between")}>
        {!collapsed && <Brand />}
        {collapsed && <Brand collapsed />}
        {showToggle && !collapsed && (
          <button type="button" onClick={onToggle} aria-label="Collapse sidebar" className="w-8 h-8 rounded-lg hover:bg-[#F0F0F0] flex items-center justify-center text-[#707070]">
            <PanelLeft className="w-4 h-4" />
          </button>
        )}
      </div>
      {showToggle && collapsed && (
        <button type="button" onClick={onToggle} aria-label="Expand sidebar" className="mx-auto mb-2 w-8 h-8 rounded-lg hover:bg-[#F0F0F0] flex items-center justify-center text-[#707070]">
          <PanelLeft className="w-4 h-4" />
        </button>
      )}
      <nav aria-label="Application" className="flex-1 overflow-y-auto px-2 pt-2">
        {!collapsed && <p className="px-2.5 pb-1.5 text-[11px] tracking-wide text-[#707070] uppercase">Career</p>}
        <div className="flex flex-col gap-0.5">{CAREER.map((i) => <NavItem key={i.to} item={i} base={base} collapsed={collapsed} onNavigate={onNavigate} />)}</div>
        {!collapsed && <p className="px-2.5 pt-5 pb-1.5 text-[11px] tracking-wide text-[#707070] uppercase">Tools</p>}
        {collapsed && <div className="h-4" />}
        <div className="flex flex-col gap-0.5">{TOOLS.map((i) => <NavItem key={i.to} item={i} base={base} collapsed={collapsed} onNavigate={onNavigate} />)}</div>
      </nav>
      <ProfileMenu collapsed={collapsed} />
    </div>
  );
}

export default function DashboardLayout() {
  const { mode, base, authLoaded, isSignedIn, plan } = useApp();
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => {
    if (!drawer) return;
    const k = (e) => e.key === "Escape" && setDrawer(false);
    document.addEventListener("keydown", k);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", k); document.body.style.overflow = ""; };
  }, [drawer]);

  if (!authLoaded) return <div className="h-screen flex items-center justify-center"><Skeleton className="w-40 h-6" /></div>;
  if (mode === "app" && !isSignedIn) return <Navigate to={`/signin?redirect_to=${encodeURIComponent(pathname)}`} replace />;

  return (
    <div className="h-screen flex bg-[#FAFAFA] text-[#161616] font-body overflow-hidden">
      <a href="#dash-main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:bg-white focus:px-3 focus:py-2 focus:rounded-md">Skip to content</a>
      <aside className={cn("hidden md:block shrink-0 border-r border-[#E7E7E7] bg-[#FAFAFA] transition-[width] duration-200", collapsed ? "w-[64px]" : "w-[232px]")}>
        <SidebarBody collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} base={base} />
      </aside>

      {drawer && (
        <div className="md:hidden fixed inset-0 z-[60] flex">
          <div className="absolute inset-0 bg-black/30" onClick={() => setDrawer(false)} aria-hidden="true" />
          <aside role="dialog" aria-modal="true" aria-label="Navigation" className="relative w-[272px] max-w-[85vw] bg-[#FAFAFA] shadow-xl">
            <SidebarBody base={base} showToggle={false} onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        <div className="md:hidden h-14 shrink-0 flex items-center gap-3 px-3 border-b border-[#E7E7E7] bg-white">
          <button type="button" onClick={() => setDrawer(true)} aria-label="Open navigation" className="w-10 h-10 rounded-lg hover:bg-[#F4F4F4] flex items-center justify-center"><Menu className="w-5 h-5" /></button>
          <Brand />
        </div>
        {mode === "demo" && (
          <div className="shrink-0 bg-[#FDF3DC] text-[#7a5600] text-[12px] px-4 py-1.5 text-center">
            Demo workspace: sample data only. No real email, AI, billing or job listings are connected.
          </div>
        )}
        {mode === "app" && !plan && (
          <div className="shrink-0 bg-[#E6F0FD] text-[#1B66C0] text-[12px] px-4 py-1.5 text-center">
            You don't have a plan yet, so AI credits are 0. <Link to="/plans" className="underline font-medium">Choose a plan</Link> (simulated checkout) or <Link to="/demo/chat" className="underline font-medium">try the demo</Link>.
          </div>
        )}
        <main id="dash-main" className="flex-1 min-h-0 overflow-y-auto">
          <Suspense fallback={<div className="p-6"><Skeleton className="h-8 w-48 mb-4" /><Skeleton className="h-64 w-full" /></div>}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <ToastViewport />
    </div>
  );
}
