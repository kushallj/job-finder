import React from "react";
import { Check, Calendar, Search, FileText, CheckCircle2, Clock, Filter, Briefcase } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function EverythingYouNeed() {
  const { everythingYouNeed } = SITE_CONTENT;

  return (
    <Section className="py-16 md:py-24 bg-[#FAFAFA] border-t border-[#F0F0F0]">
      <div className="mx-auto max-w-[820px] text-center">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4">
          <span>{everythingYouNeed.eyebrow}</span>
        </div>

        {/* Heading */}
        <Reveal>
          <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
            {everythingYouNeed.heading}
          </h2>
          <p className="mt-3.5 mx-auto max-w-[480px] font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {everythingYouNeed.description}
          </p>
        </Reveal>
      </div>

      {/* 2x2 Feature Grid */}
      <div className="mt-12 md:mt-16 mx-auto max-w-[1040px] grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* CARD 01: Application Tracking */}
        <div className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-7 flex flex-col justify-between shadow-subtle hover:border-[#D0D0D0] transition-colors">
          {/* Mini UI Demonstration */}
          <div className="w-full rounded-xl bg-[#141414] text-white p-4 mb-6 shadow-inner text-left font-body">
            <div className="flex items-center justify-between text-[11px] text-white/60 mb-3 pb-2 border-b border-white/10">
              <span className="font-medium text-white/80">Application Pipeline</span>
              <span className="text-[#4ADE80]">Active Synced</span>
            </div>
            <div className="space-y-2 text-[12px]">
              <div className="p-2 rounded bg-white/5 border border-white/10 flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">Stripe · Full Stack</div>
                  <div className="text-[11px] text-white/50">Applied 3 days ago</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[11px]">Under Review</span>
              </div>
              <div className="p-2 rounded bg-white/5 border border-white/10 flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">Linear · Product Design</div>
                  <div className="text-[11px] text-white/50">Applied 1 week ago</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[11px]">Interview Round 2</span>
              </div>
            </div>
          </div>

          <div>
            <span className="text-[11.5px] font-body font-bold text-[#888888] tracking-wider uppercase">
              {everythingYouNeed.cards[0].eyebrow}
            </span>
            <h3 className="font-display font-medium text-card-h3 text-[#161616] mt-1 mb-2">
              {everythingYouNeed.cards[0].title}
            </h3>
            <p className="font-body text-[14px] text-[#626262] leading-relaxed">
              {everythingYouNeed.cards[0].description}
            </p>
          </div>
        </div>

        {/* CARD 02: Smart Job Discovery */}
        <div className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-7 flex flex-col justify-between shadow-subtle hover:border-[#D0D0D0] transition-colors">
          {/* Mini UI Demonstration */}
          <div className="w-full rounded-xl bg-[#F7F7F7] border border-[#E8E8E8] p-4 mb-6 text-left font-body">
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-3.5 h-3.5 text-[#888888]" />
              <span className="text-[12px] font-medium text-[#161616]">Search Preferences</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="px-2.5 py-1 rounded-full bg-white border border-[#E0E0E0] text-[11px] text-[#161616] font-medium">Remote only</span>
              <span className="px-2.5 py-1 rounded-full bg-white border border-[#E0E0E0] text-[11px] text-[#161616] font-medium">Software Engineer</span>
              <span className="px-2.5 py-1 rounded-full bg-[#141414] text-white text-[11px] font-medium">$120k+</span>
            </div>
            <div className="p-2.5 rounded-lg bg-white border border-[#E8E8E8] text-[12px]">
              <div className="font-medium text-[#161616]">Found 18 matched opportunities this week</div>
              <div className="text-[11px] text-[#888888]">Direct company postings verified</div>
            </div>
          </div>

          <div>
            <span className="text-[11.5px] font-body font-bold text-[#888888] tracking-wider uppercase">
              {everythingYouNeed.cards[1].eyebrow}
            </span>
            <h3 className="font-display font-medium text-card-h3 text-[#161616] mt-1 mb-2">
              {everythingYouNeed.cards[1].title}
            </h3>
            <p className="font-body text-[14px] text-[#626262] leading-relaxed">
              {everythingYouNeed.cards[1].description}
            </p>
          </div>
        </div>

        {/* CARD 03: Resume Management */}
        <div className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-7 flex flex-col justify-between shadow-subtle hover:border-[#D0D0D0] transition-colors">
          {/* Mini UI Demonstration */}
          <div className="w-full rounded-xl bg-[#F7F7F7] border border-[#E8E8E8] p-4 mb-6 text-left font-body">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#161616]" />
                <span className="text-[12px] font-medium text-[#161616]">Targeted Career Profile</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#DCFCE7] text-[#15803D] font-medium">Updated</span>
            </div>
            <div className="space-y-1.5 p-2.5 rounded-lg bg-white border border-[#E8E8E8] text-[11px] text-[#626262]">
              <div className="flex items-center gap-1.5 text-[#161616] font-medium">
                <Check className="w-3 h-3 text-[#238636]" />
                <span>Primary: Full Stack & React Specialist Resume</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Check className="w-3 h-3 text-[#238636]" />
                <span>Secondary: Systems & Architecture Resume</span>
              </div>
            </div>
          </div>

          <div>
            <span className="text-[11.5px] font-body font-bold text-[#888888] tracking-wider uppercase">
              {everythingYouNeed.cards[2].eyebrow}
            </span>
            <h3 className="font-display font-medium text-card-h3 text-[#161616] mt-1 mb-2">
              {everythingYouNeed.cards[2].title}
            </h3>
            <p className="font-body text-[14px] text-[#626262] leading-relaxed">
              {everythingYouNeed.cards[2].description}
            </p>
          </div>
        </div>

        {/* CARD 04: Organized Follow-Ups */}
        <div className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-7 flex flex-col justify-between shadow-subtle hover:border-[#D0D0D0] transition-colors">
          {/* Mini UI Demonstration */}
          <div className="w-full rounded-xl bg-[#F7F7F7] border border-[#E8E8E8] p-4 mb-6 text-left font-body">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#161616]" />
                <span className="text-[12px] font-medium text-[#161616]">Upcoming Milestones</span>
              </div>
              <span className="text-[11px] text-[#888888]">This Week</span>
            </div>
            <div className="space-y-1.5">
              <div className="p-2 rounded bg-white border border-[#E8E8E8] flex items-center justify-between text-[11.5px]">
                <span className="font-medium text-[#161616]">Acme Corp Technical Interview</span>
                <span className="text-[#D99A22] font-medium">Tomorrow 10 AM</span>
              </div>
              <div className="p-2 rounded bg-white border border-[#E8E8E8] flex items-center justify-between text-[11.5px]">
                <span className="text-[#626262]">Follow up with Notion hiring manager</span>
                <span className="text-[#888888]">Friday</span>
              </div>
            </div>
          </div>

          <div>
            <span className="text-[11.5px] font-body font-bold text-[#888888] tracking-wider uppercase">
              {everythingYouNeed.cards[3].eyebrow}
            </span>
            <h3 className="font-display font-medium text-card-h3 text-[#161616] mt-1 mb-2">
              {everythingYouNeed.cards[3].title}
            </h3>
            <p className="font-body text-[14px] text-[#626262] leading-relaxed">
              {everythingYouNeed.cards[3].description}
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}
