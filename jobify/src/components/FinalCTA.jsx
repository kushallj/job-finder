import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";

export default function FinalCTA() {
  const { finalCta } = SITE_CONTENT;

  return (
    <Section className="py-20 md:py-28 bg-white">
      <div className="relative mx-auto max-w-[960px] rounded-3xl bg-[#F7F7F7] border border-[#E8E8E8] px-6 sm:px-12 py-16 md:py-20 text-center overflow-hidden">
        {/* Subtle dot pattern accents on the left and right */}
        <div
          className="absolute left-0 top-0 bottom-0 w-36 pointer-events-none opacity-40"
          style={{
            backgroundImage: "radial-gradient(#C5C5C5 1px, transparent 1px)",
            backgroundSize: "16px 16px",
            maskImage: "linear-gradient(to right, black, transparent)",
          }}
          aria-hidden="true"
        />
        <div
          className="absolute right-0 top-0 bottom-0 w-36 pointer-events-none opacity-40"
          style={{
            backgroundImage: "radial-gradient(#C5C5C5 1px, transparent 1px)",
            backgroundSize: "16px 16px",
            maskImage: "linear-gradient(to left, black, transparent)",
          }}
          aria-hidden="true"
        />

        <div className="relative z-10 max-w-[620px] mx-auto flex flex-col items-center">
          <div className="w-10 h-10 rounded-full bg-white border border-[#E8E8E8] shadow-xs flex items-center justify-center text-[#161616] mb-5">
            <Sparkles className="w-5 h-5" />
          </div>

          <Reveal>
            <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
              {finalCta.heading}
            </h2>
            <p className="mt-4 font-body text-[16px] md:text-[17px] text-[#626262] leading-relaxed max-w-[480px]">
              {finalCta.description}
            </p>
          </Reveal>

          <div className="mt-8">
            <Link
              to={finalCta.buttonHref}
              className="inline-flex items-center justify-center gap-2 h-[48px] px-8 rounded-full bg-[#141414] text-white text-[15px] font-medium transition-all duration-150 hover:bg-[#2A2A2A] active:scale-[0.98] shadow-sm"
            >
              <span>{finalCta.buttonLabel}</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </Section>
  );
}
