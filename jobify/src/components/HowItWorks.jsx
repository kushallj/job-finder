import React, { useState } from "react";
import { Search, Compass, CheckCircle, FileText, Calendar, ArrowRight, Clock, Star, Bell } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function HowItWorks() {
  const { howItWorks } = SITE_CONTENT;
  const [activeStep, setActiveStep] = useState("search");

  return (
    <Section id="how-it-works" className="py-16 md:py-24 bg-white">
      <div className="mx-auto max-w-[820px] text-center">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4">
          <span>{howItWorks.eyebrow}</span>
        </div>

        {/* Heading */}
        <Reveal>
          <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
            {howItWorks.heading}
          </h2>
          <p className="mt-3.5 mx-auto max-w-[480px] font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {howItWorks.description}
          </p>
        </Reveal>
      </div>

      {/* Main Interactive Product Preview Showcase */}
      <div className="mt-12 md:mt-16 mx-auto max-w-[960px]">
        <div className="rounded-2xl bg-[#141414] text-white p-6 sm:p-8 shadow-app overflow-hidden relative">
          {/* Subtle glow / grid in the background */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage:
                "radial-gradient(circle at 50% 0%, #FFFFFF 1px, transparent 1px)",
              backgroundSize: "24px 24px",
            }}
          />

          {/* Step Selector Tab Bar inside the preview */}
          <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 pb-6 border-b border-white/10">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
              <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
              <span className="w-2.5 h-2.5 rounded-full bg-white/20" />
              <span className="text-[12px] font-body text-white/50 ml-2">Jobify Workflow Engine</span>
            </div>
            <div className="flex items-center gap-1.5 p-1 bg-white/5 rounded-lg border border-white/10">
              {howItWorks.steps.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setActiveStep(s.id)}
                  className={cn(
                    "px-3 py-1 rounded-md text-[12px] font-body font-medium transition-colors",
                    activeStep === s.id
                      ? "bg-white text-[#141414]"
                      : "text-white/60 hover:text-white"
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic Content Views corresponding to the selected capability */}
          <div className="relative z-10 py-6 min-h-[220px] flex items-center justify-center">
            {activeStep === "search" && (
              <div className="w-full max-w-[720px] space-y-3">
                <div className="flex items-center gap-3 p-3.5 rounded-xl bg-white/5 border border-white/10">
                  <Search className="w-4 h-4 text-white/60 shrink-0" />
                  <span className="text-[13px] text-white/80 font-body">
                    Role: "Frontend Developer" · Location: "Remote" · Experience: "Mid / Senior"
                  </span>
                  <span className="ml-auto text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/90">
                    42 Matches
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-white/5 border border-white/10 text-left">
                    <div className="text-[13px] font-bold text-white">Acme Corp</div>
                    <div className="text-[12px] text-white/70">Senior React Engineer · $140k - $160k</div>
                    <div className="mt-2 flex items-center gap-1 text-[11px] text-[#4ADE80]">
                      <Star className="w-3 h-3 fill-current" /> 98% Profile Match
                    </div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-white/5 border border-white/10 text-left">
                    <div className="text-[13px] font-bold text-white">Linear</div>
                    <div className="text-[12px] text-white/70">UI/UX Systems Engineer · Remote</div>
                    <div className="mt-2 flex items-center gap-1 text-[11px] text-[#4ADE80]">
                      <Star className="w-3 h-3 fill-current" /> 95% Profile Match
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeStep === "track" && (
              <div className="w-full max-w-[720px] grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-left text-[12px]">
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-white/50 text-[11px] mb-2 font-medium">SAVED (12)</div>
                  <div className="p-2 rounded bg-white/10 mb-1.5 font-medium text-white">Stripe</div>
                  <div className="p-2 rounded bg-white/10 font-medium text-white">Figma</div>
                </div>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-[#60A5FA] text-[11px] mb-2 font-medium">APPLIED (8)</div>
                  <div className="p-2 rounded bg-white/10 mb-1.5 font-medium text-white">Notion</div>
                  <div className="p-2 rounded bg-white/10 font-medium text-white">Vercel</div>
                </div>
                <div className="p-3 rounded-xl bg-white/10 border border-white/20">
                  <div className="text-[#FBBF24] text-[11px] mb-2 font-medium">INTERVIEW (3)</div>
                  <div className="p-2 rounded bg-white/20 mb-1.5 font-medium text-white">Acme Corp</div>
                  <div className="p-2 rounded bg-white/20 font-medium text-white">Linear</div>
                </div>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <div className="text-[#4ADE80] text-[11px] mb-2 font-medium">OFFER (1)</div>
                  <div className="p-2 rounded bg-[#238636]/40 font-medium text-[#86EFAC]">Studio North</div>
                </div>
              </div>
            )}

            {activeStep === "prepare" && (
              <div className="w-full max-w-[640px] p-4 rounded-xl bg-white/5 border border-white/10 text-left">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-white/80" />
                    <span className="text-[13px] font-medium text-white">Resume_Software_Eng_2026.pdf</span>
                  </div>
                  <span className="text-[11px] text-[#4ADE80] bg-[#4ADE80]/10 px-2 py-0.5 rounded">Ready for Review</span>
                </div>
                <div className="space-y-1.5 text-[12px] text-white/70">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-[#4ADE80]" />
                    <span>Keyword alignment checked for 14 saved engineering job descriptions</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-[#4ADE80]" />
                    <span>Portfolio and GitHub project links verified</span>
                  </div>
                </div>
              </div>
            )}

            {activeStep === "organize" && (
              <div className="w-full max-w-[640px] space-y-2 text-left">
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Calendar className="w-4 h-4 text-[#FBBF24]" />
                    <div>
                      <div className="text-[13px] font-medium text-white">Acme Technical Screen</div>
                      <div className="text-[11px] text-white/60">Tomorrow at 10:00 AM PST with Engineering Manager</div>
                    </div>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/80">Prep Sheet</span>
                </div>
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Bell className="w-4 h-4 text-[#60A5FA]" />
                    <div>
                      <div className="text-[13px] font-medium text-white">Follow-up with Linear Recruiter</div>
                      <div className="text-[11px] text-white/60">Sent 4 days ago · Gentle nudge scheduled for Thursday</div>
                    </div>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/80">Template</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Four Capability Columns Below */}
      <div className="mt-14 md:mt-18 mx-auto max-w-[1040px] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {howItWorks.steps.map((step) => {
          const isSelected = activeStep === step.id;

          return (
            <div
              key={step.num}
              onClick={() => setActiveStep(step.id)}
              className={cn(
                "cursor-pointer p-4 rounded-xl transition-all duration-200 text-left border",
                isSelected
                  ? "bg-[#F7F7F7] border-[#141414] shadow-xs"
                  : "bg-white border-transparent hover:border-[#E8E8E8]"
              )}
            >
              <div className="text-[12px] font-bold text-[#888888] font-body tracking-wider mb-2">
                {step.num}. {step.label}
              </div>
              <h3 className="font-display font-medium text-[17px] text-[#161616] mb-2 leading-snug">
                {step.title}
              </h3>
              <p className="font-body text-[13.5px] text-[#626262] leading-relaxed">
                {step.description}
              </p>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
