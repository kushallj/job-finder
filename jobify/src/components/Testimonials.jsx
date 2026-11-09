import React from "react";
import { Quote } from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";

export default function Testimonials() {
  const { testimonials } = SITE_CONTENT;

  return (
    <Section className="py-16 md:py-24 bg-[#FAFAFA] border-t border-[#F0F0F0]">
      <div className="mx-auto max-w-[820px] text-center">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4">
          <span>{testimonials.eyebrow}</span>
        </div>

        {/* Heading */}
        <Reveal>
          <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
            {testimonials.heading}
          </h2>
          <p className="mt-3.5 mx-auto max-w-[480px] font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {testimonials.description}
          </p>
        </Reveal>
      </div>

      {/* Testimonial Cards Grid */}
      <div className="mt-12 md:mt-16 mx-auto max-w-[1040px] grid grid-cols-1 md:grid-cols-3 gap-6">
        {testimonials.items.map((item) => (
          <div
            key={item.id}
            className="rounded-2xl bg-white border border-[#E8E8E8] p-6 sm:p-7 flex flex-col justify-between shadow-subtle hover:border-[#D0D0D0] transition-colors text-left"
          >
            <div>
              <Quote className="w-6 h-6 text-[#141414]/20 mb-4" />
              <p className="font-body text-[14.5px] text-[#161616] leading-relaxed">
                "{item.quote}"
              </p>
            </div>

            <div className="mt-6 pt-5 border-t border-[#F0F0F0] flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#141414] text-white flex items-center justify-center text-[12px] font-bold shrink-0">
                {item.avatarInitials}
              </div>
              <div>
                <div className="font-body font-bold text-[14px] text-[#161616] leading-tight">
                  {item.name}
                </div>
                <div className="text-[12px] text-[#888888] font-body">
                  {item.role} · {item.org}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Honest preview disclaimer */}
      <div className="mt-8 text-center">
        <p className="text-[12px] font-body text-[#888888] italic">
          {testimonials.disclaimer}
        </p>
      </div>
    </Section>
  );
}
