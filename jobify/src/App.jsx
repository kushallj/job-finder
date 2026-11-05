import React, { Suspense, lazy, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import { AppProvider } from "./app/AppProvider.jsx";
import DashboardLayout from "./app/DashboardLayout.jsx";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import JobCategories from "./components/JobCategories.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import EverythingYouNeed from "./components/EverythingYouNeed.jsx";
import Pricing from "./components/Pricing.jsx";
import Testimonials from "./components/Testimonials.jsx";
import FAQ from "./components/FAQ.jsx";
import Contact from "./components/Contact.jsx";
import FinalCTA from "./components/FinalCTA.jsx";
import Footer from "./components/Footer.jsx";
import StubPage from "./components/StubPage.jsx";
import NotFound from "./components/NotFound.jsx";
import { STUB_ROUTES } from "./data/routes.js";
import { useScrollToHash } from "./hooks/useScrollToHash.js";

const ChatPage = lazy(() => import("./app/pages/ChatPage.jsx"));
const JobsPage = lazy(() => import("./app/pages/JobsPage.jsx"));
const ApplicationsPage = lazy(() => import("./app/pages/ApplicationsPage.jsx"));
const FoundersPage = lazy(() => import("./app/pages/FoundersPage.jsx"));
const PortfolioPage = lazy(() => import("./app/pages/PortfolioPage.jsx"));
const SignInPage = lazy(() => import("./app/pages/SignInPage.jsx"));
const PlansPage = lazy(() => import("./app/pages/PlansPage.jsx"));
const CheckoutPage = lazy(() => import("./app/pages/CheckoutPage.jsx"));

function SignupRedirect() {
  const { search } = useLocation();
  return <Navigate to={`/plans${search}`} replace />;
}

const workspace = (
  <>
    <Route index element={<Navigate to="chat" replace />} />
    <Route path="chat" element={<ChatPage />} />
    <Route path="jobs" element={<JobsPage />} />
    <Route path="applications" element={<ApplicationsPage />} />
    <Route path="founders" element={<FoundersPage />} />
    <Route path="portfolio" element={<PortfolioPage />} />
  </>
);

/**
 * Main Jobify Landing Page
 * Faithfully following the 11-section information architecture of Aarivi:
 * 01. Header & Navigation (rendered by layout wrapper)
 * 02. Hero / Product Demonstration
 * 03. Explore Job Categories
 * 04. How Jobify Works
 * 05. Everything You Need
 * 06. Pricing Plans
 * 07. Customer Testimonials
 * 08. Frequently Asked Questions
 * 09. Get in Touch / Contact Form
 * 10. Final Conversion CTA
 * 11. Footer (rendered by layout wrapper)
 */
function HomePage() {
  useEffect(() => {
    document.title = "Jobify - Job Search & Application Management";
  }, []);

  return (
    <main id="main-content">
      {/* 02. Hero / Product Demonstration */}
      <Hero />

      {/* 03. Explore Job Categories */}
      <JobCategories />

      {/* 04. How Jobify Works */}
      <HowItWorks />

      {/* 05. Everything You Need */}
      <EverythingYouNeed />

      {/* 06. Pricing Plans */}
      <Pricing />

      {/* 07. Customer Testimonials */}
      <Testimonials />

      {/* 08. Frequently Asked Questions */}
      <FAQ />

      {/* 09. Get in Touch / Contact Form */}
      <Contact />

      {/* 10. Final Conversion CTA */}
      <FinalCTA />
    </main>
  );
}

/**
 * Layout orchestrator with persistent Navbar, Router, and Footer
 */
function PublicLayout() {
  useScrollToHash();
  return (
    <div className="min-h-screen flex flex-col bg-white text-[#161616]">
      {/* 01. Header & Navigation */}
      <Navbar />
      <div className="flex-1"><Outlet /></div>
      {/* 11. Footer */}
      <Footer />
    </div>
  );
}

function AppContent() {
  return (
    <Suspense fallback={<div className="min-h-screen" aria-busy="true" />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/404" element={<NotFound />} />
          {STUB_ROUTES.map((route) => (
            <Route key={route.path} path={route.path} element={<StubPage title={route.title} description={route.description} />} />
          ))}
        </Route>

        {/* Account flow */}
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/login" element={<Navigate to="/signin" replace />} />
        <Route path="/signup" element={<SignupRedirect />} />
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />

        {/* Product workspaces: /demo is open sample data, /app requires a Clerk session */}
        <Route path="/demo" element={<DashboardLayout />}>{workspace}</Route>
        <Route path="/app" element={<DashboardLayout />}>{workspace}</Route>

        <Route element={<PublicLayout />}><Route path="*" element={<NotFound />} /></Route>
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppContent />
      </AppProvider>
    </BrowserRouter>
  );
}
