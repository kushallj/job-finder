import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Search, Filter, Briefcase, Calendar, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function Hero() {
  const { hero } = SITE_CONTENT;

  return (
    <section
      id="top"
      className="relative w-full overflow-hidden pt-12 md:pt-20 pb-16 md:pb-24 bg-white"
      aria-label="Introduction"
    >
      {/* Subtle Halftone Pattern on Outer Left and Right Flanks */}
      <div
        className="hidden md:block absolute left-0 top-0 bottom-0 w-[240px] lg:w-[320px] bg-halftone-left pointer-events-none opacity-60 z-0"
        aria-hidden="true"
      />
      <div
        className="hidden md:block absolute right-0 top-0 bottom-0 w-[240px] lg:w-[320px] bg-halftone-right pointer-events-none opacity-60 z-0"
        aria-hidden="true"
      />

      <div className="relative z-10 mx-auto w-full max-w-[1120px] px-6 md:px-8 text-center flex flex-col items-center">
        {/* Eyebrow Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[12px] font-body font-medium text-[#626262] tracking-wide mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-[#238636]" />
          <span>{hero.eyebrow}</span>
        </div>

        {/* Main Headline */}
        <h1 className="font-display text-hero-h1 text-[#161616] tracking-tight max-w-[820px]">
          {hero.headline}
        </h1>

        {/* Supporting Description */}
        <p className="mt-5 max-w-[560px] font-body text-[16px] md:text-[17px] text-[#626262] leading-relaxed">
          {hero.description}
        </p>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 w-full sm:w-auto">
          <Link
            to={hero.primaryCta.href}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 h-[46px] px-7 rounded-full bg-[#141414] text-white text-[14.5px] font-medium transition-all duration-150 hover:bg-[#2A2A2A] active:scale-[0.98] shadow-sm"
          >
            <span>{hero.primaryCta.label}</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to={hero.secondaryCta.href}
            className="w-full sm:w-auto inline-flex items-center justify-center h-[46px] px-6 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[#161616] text-[14.5px] font-medium transition-all duration-150 hover:bg-[#EFEFEF] active:scale-[0.98]"
          >
            {hero.secondaryCta.label}
          </Link>
        </div>

        {/* Product Demonstration: Large Realistic Jobify Dashboard Preview */}
        <div className="mt-14 md:mt-18 w-full max-w-[980px]">
          <div className="relative rounded-2xl bg-white border border-[#E8E8E8] shadow-app overflow-hidden text-left">
            {/* Top Window Bar */}
            <div className="h-10 px-4 bg-[#F9F9F9] border-b border-[#E8E8E8] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                <span className="ml-3 text-[12px] font-body text-[#888888] font-medium hidden sm:inline">
                  jobify.app/dashboard
                </span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-body text-[#888888] bg-white border border-[#E8E8E8]">
                <span>Demo Workspace</span>
              </div>
            </div>

            {/* Application Main Layout */}
            <div className="flex flex-col md:flex-row min-h-[380px]">
              {/* Left Mini Sidebar */}
              <div className="hidden md:flex w-[200px] bg-[#FDFDFD] border-r border-[#E8E8E8] p-4 flex-col justify-between shrink-0">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 px-2 py-1 text-[13px] font-bold text-[#161616]">
                    <div className="w-4 h-4 rounded bg-[#141414] text-white flex items-center justify-center text-[10px]">J</div>
                    <span>My Job Hunt</span>
                  </div>
                  <nav className="space-y-1 text-[13px] font-body">
                    <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-[#F2F2F2] text-[#161616] font-medium">
                      <span className="flex items-center gap-2">
                        <Briefcase className="w-3.5 h-3.5" />
                        Applications
                      </span>
                      <span className="text-[11px] px-1.5 py-0.2 rounded bg-white border border-[#E0E0E0]">5</span>
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[#626262] hover:bg-[#F7F7F7]">
                      <Search className="w-3.5 h-3.5" />
                      Saved Roles
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[#626262] hover:bg-[#F7F7F7]">
                      <Calendar className="w-3.5 h-3.5" />
                      Interviews
                    </div>
                  </nav>
                </div>

                <div className="p-2.5 rounded-lg bg-[#F7F7F7] border border-[#E8E8E8] text-[11px] text-[#626262]">
                  <div className="font-medium text-[#161616]">Active Tracker</div>
                  <div>3 in progress, 1 offer</div>
                </div>
              </div>

              {/* Main Content Area: Applications Table */}
              <div className="flex-1 p-4 sm:p-6 bg-white overflow-x-auto">
                {/* Search & Filter Toolbar */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-[#F0F0F0]">
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <div className="relative w-full sm:w-[260px]">
                      <Search className="w-3.5 h-3.5 text-[#888888] absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        readOnly
                        value="Search applications..."
                        className="w-full h-8 pl-8 pr-3 text-[12px] bg-[#F7F7F7] border border-[#E8E8E8] rounded-md text-[#626262] outline-none cursor-default"
                      />
                    </div>
                    <button
                      type="button"
                      className="h-8 px-2.5 rounded-md border border-[#E8E8E8] bg-white text-[12px] text-[#626262] inline-flex items-center gap-1.5 shrink-0"
                    >
                      <Filter className="w-3 h-3" />
                      <span>Filter</span>
                    </button>
                  </div>
                  <div className="text-[12px] text-[#888888] font-body">
                    Showing 5 active applications
                  </div>
                </div>

                {/* Applications Table List */}
                <div className="divide-y divide-[#F0F0F0] text-[13px] font-body">
                  {hero.demoApplications.map((app) => (
                    <div
                      key={app.id}
                      className="py-3 px-2 flex items-center justify-between gap-4 hover:bg-[#FAFAFA] rounded-md transition-colors"
                    >
                      {/* Company & Role */}
                      <div className="flex items-center gap-3 min-w-[180px]">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-[11px] font-bold shrink-0"
                          style={{ backgroundColor: app.companyBg }}
                        >
                          {app.companyInitials}
                        </div>
                        <div>
                          <div className="font-medium text-[#161616] leading-snug">
                            {app.title}
                          </div>
                          <div className="text-[11.5px] text-[#888888]">
                            {app.company} · {app.type}
                          </div>
                        </div>
                      </div>

                      {/* Location (hidden on very small viewports) */}
                      <div className="hidden sm:block text-[12px] text-[#626262]">
                        {app.location}
                      </div>

                      {/* Applied Date */}
                      <div className="hidden md:block text-[12px] text-[#888888]">
                        {app.appliedDate}
                      </div>

                      {/* Status Badge */}
                      <div className="shrink-0 flex items-center gap-2">
                        {app.status === "Interview" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium bg-[#FEF3C7] text-[#92400E]">
                            <Clock className="w-3 h-3" />
                            {app.status}
                          </span>
                        )}
                        {app.status === "Offer" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium bg-[#DCFCE7] text-[#15803D]">
                            <CheckCircle2 className="w-3 h-3" />
                            {app.status}
                          </span>
                        )}
                        {app.status === "Applied" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium bg-[#EFF6FF] text-[#1D4ED8]">
                            {app.status}
                          </span>
                        )}
                        {app.status === "Review" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium bg-[#F3E8FF] text-[#7E22CE]">
                            {app.status}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Dashboard Footer Note */}
            <div className="px-4 py-2 bg-[#F9F9F9] border-t border-[#E8E8E8] text-right">
              <span className="text-[11px] text-[#888888] font-body italic">
                Illustrative preview interface with sample records
              </span>
            </div>
          </div>
        </div>

        {/* Hero Brand Strip */}
        <div className="mt-12 md:mt-16 w-full pt-6 border-t border-[#F0F0F0]">
          <p className="text-[12px] font-body uppercase tracking-wider text-[#888888] mb-4">
            Track applications across industry leaders
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-14 opacity-60">
            {hero.supportingCompanies.map((c) => (
              <span
                key={c.name}
                className="font-display text-[15px] md:text-[17px] font-bold tracking-tight text-[#161616]"
              >
                {c.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
