import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Sparkles } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function Pricing() {
  const { pricing } = SITE_CONTENT;
  const [isYearly, setIsYearly] = useState(true);

  return (
    <Section id="pricing" className="py-16 md:py-24 bg-white">
      <div className="mx-auto max-w-[820px] text-center">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4">
          <span>{pricing.eyebrow}</span>
        </div>

        {/* Heading */}
        <Reveal>
          <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
            {pricing.heading}
          </h2>
          <p className="mt-3.5 mx-auto max-w-[480px] font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {pricing.description}
          </p>
        </Reveal>

        {/* Billing Toggle */}
        <div className="mt-8 flex items-center justify-center gap-3">
          <span
            className={cn(
              "text-[14px] font-body transition-colors",
              !isYearly ? "text-[#161616] font-medium" : "text-[#888888]"
            )}
          >
            Monthly billing
          </span>

          <button
            type="button"
            role="switch"
            aria-checked={isYearly}
            aria-label="Toggle annual billing discount"
            onClick={() => setIsYearly(!isYearly)}
            className={cn(
              "w-12 h-6 rounded-full p-0.5 transition-colors duration-200 ease-in-out cursor-pointer relative",
              isYearly ? "bg-[#141414]" : "bg-[#D5D5D5]"
            )}
          >
            <div
              className={cn(
                "w-5 h-5 rounded-full bg-white transition-transform duration-200 ease-in-out",
                isYearly ? "translate-x-6" : "translate-x-0"
              )}
            />
          </button>

          <span
            className={cn(
              "text-[14px] font-body flex items-center gap-2 transition-colors",
              isYearly ? "text-[#161616] font-medium" : "text-[#888888]"
            )}
          >
            Annual billing
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#DCFCE7] text-[#15803D]">
              Save 20%
            </span>
          </span>
        </div>
      </div>

      {/* Two Plan Cards */}
      <div className="mt-12 md:mt-16 mx-auto max-w-[840px] grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
        {pricing.plans.map((plan) => {
          const price = isYearly ? plan.yearlyPrice : plan.monthlyPrice;

          return (
            <div
              key={plan.id}
              className={cn(
                "rounded-2xl p-7 sm:p-8 flex flex-col justify-between transition-all duration-200 border",
                plan.isPopular
                  ? "bg-[#141414] text-white border-[#141414] shadow-app relative"
                  : "bg-white text-[#161616] border-[#E8E8E8] shadow-subtle hover:border-[#D0D0D0]"
              )}
            >
              {/* Card Header */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span
                    className={cn(
                      "text-[12px] font-body font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-md",
                      plan.isPopular
                        ? "bg-white/10 text-white"
                        : "bg-[#F2F2F2] text-[#626262]"
                    )}
                  >
                    {plan.badge}
                  </span>
                  {plan.isPopular && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#4ADE80]">
                      <Sparkles className="w-3 h-3" />
                      Most Popular
                    </span>
                  )}
                </div>

                <h3
                  className={cn(
                    "font-display font-bold text-[24px] tracking-tight",
                    plan.isPopular ? "text-white" : "text-[#161616]"
                  )}
                >
                  {plan.name}
                </h3>

                <p
                  className={cn(
                    "mt-2 text-[14px] font-body leading-relaxed",
                    plan.isPopular ? "text-white/70" : "text-[#626262]"
                  )}
                >
                  {plan.description}
                </p>

                {/* Price Display */}
                <div className="mt-6 mb-6 pb-6 border-b border-current/10">
                  <div className="flex items-baseline gap-1">
                    <span
                      className={cn(
                        "font-display text-[42px] font-bold tracking-tight",
                        plan.isPopular ? "text-white" : "text-[#161616]"
                      )}
                    >
                      ${price}
                    </span>
                    <span
                      className={cn(
                        "text-[14px] font-body",
                        plan.isPopular ? "text-white/60" : "text-[#888888]"
                      )}
                    >
                      /{plan.id === "free" ? "forever" : "month"}
                    </span>
                  </div>
                  {isYearly && plan.id !== "free" && (
                    <div className="text-[11.5px] text-[#4ADE80] font-body mt-1">
                      Billed annually ($84/year)
                    </div>
                  )}
                </div>

                {/* Features List */}
                <div className="space-y-3">
                  <div
                    className={cn(
                      "text-[12px] font-bold uppercase tracking-wider",
                      plan.isPopular ? "text-white/60" : "text-[#888888]"
                    )}
                  >
                    Included in {plan.name}:
                  </div>
                  <ul className="space-y-2.5 text-[13.5px] font-body">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2.5">
                        <Check
                          className={cn(
                            "w-4 h-4 shrink-0 mt-0.5",
                            plan.isPopular ? "text-[#4ADE80]" : "text-[#238636]"
                          )}
                        />
                        <span className={plan.isPopular ? "text-white/90" : "text-[#161616]"}>
                          {feature}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-8 pt-4">
                <Link
                  to={plan.ctaHref}
                  className={cn(
                    "w-full h-[46px] rounded-full flex items-center justify-center text-[14.5px] font-medium transition-all duration-150 active:scale-[0.98]",
                    plan.isPopular
                      ? "bg-white text-[#141414] hover:bg-[#F2F2F2] shadow-sm"
                      : "bg-[#141414] text-white hover:bg-[#2A2A2A]"
                  )}
                >
                  {plan.ctaLabel}
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Transparent Disclaimer */}
      <div className="mt-8 text-center">
        <p className="text-[12px] font-body text-[#888888]">
          {pricing.disclaimer}
        </p>
      </div>
    </Section>
  );
}
