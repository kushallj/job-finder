import React, { useState, useRef } from "react";
import { Plus, Minus, HelpCircle } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

export default function FAQ() {
  const { faq } = SITE_CONTENT;
  const [openIndex, setOpenIndex] = useState(0); // First question open by default
  const questionRefs = useRef([]);

  const toggleQuestion = (idx) => {
    setOpenIndex(openIndex === idx ? -1 : idx);
  };

  const handleKeyDown = (e, index) => {
    let nextIndex = null;
    if (e.key === "ArrowDown") {
      nextIndex = (index + 1) % faq.items.length;
    } else if (e.key === "ArrowUp") {
      nextIndex = (index - 1 + faq.items.length) % faq.items.length;
    } else if (e.key === "Home") {
      nextIndex = 0;
    } else if (e.key === "End") {
      nextIndex = faq.items.length - 1;
    }

    if (nextIndex !== null) {
      e.preventDefault();
      questionRefs.current[nextIndex]?.focus();
    }
  };

  return (
    <Section id="faq" className="py-16 md:py-24 bg-white border-t border-[#F0F0F0]">
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-10 lg:gap-16 items-start">
        {/* Left Column: Heading and Context */}
        <div className="flex flex-col text-left">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#F7F7F7] border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4 w-fit">
            <HelpCircle className="w-3.5 h-3.5 text-[#161616]" />
            <span>{faq.eyebrow}</span>
          </div>

          <Reveal>
            <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
              {faq.heading}
            </h2>
            <p className="mt-3.5 font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed max-w-[420px]">
              {faq.description}
            </p>

            <div className="mt-8 p-4 rounded-xl bg-[#F7F7F7] border border-[#E8E8E8] max-w-[380px]">
              <div className="font-medium text-[13.5px] text-[#161616] font-body">
                Still have questions?
              </div>
              <div className="text-[12.5px] text-[#626262] font-body mt-1">
                Reach out anytime via our{" "}
                <a href="#contact" className="underline hover:text-[#161616]">
                  contact form
                </a>{" "}
                or email us at support@jobify.app.
              </div>
            </div>
          </Reveal>
        </div>

        {/* Right Column: Accessible Expandable Accordion List */}
        <div className="divide-y divide-[#E8E8E8] w-full">
          {faq.items.map((item, idx) => {
            const isOpen = openIndex === idx;

            return (
              <div key={idx} className="py-4.5 sm:py-5">
                <h3>
                  <button
                    type="button"
                    ref={(el) => (questionRefs.current[idx] = el)}
                    id={`faq-btn-${idx}`}
                    aria-expanded={isOpen}
                    aria-controls={`faq-answer-${idx}`}
                    onClick={() => toggleQuestion(idx)}
                    onKeyDown={(e) => handleKeyDown(e, idx)}
                    className="w-full flex items-center justify-between text-left gap-4 py-1 group focus-visible:rounded-sm cursor-pointer"
                  >
                    <span
                      className={cn(
                        "font-body text-[15px] sm:text-[16px] transition-colors leading-snug",
                        isOpen
                          ? "text-[#161616] font-semibold"
                          : "text-[#161616] font-normal group-hover:text-[#626262]"
                      )}
                    >
                      {item.q}
                    </span>

                    <div className="w-[28px] h-[28px] rounded-full bg-[#F2F2F2] group-hover:bg-[#E8E8E8] flex items-center justify-center shrink-0 text-[#161616] transition-colors">
                      {isOpen ? (
                        <Minus className="w-3.5 h-3.5 stroke-[2]" />
                      ) : (
                        <Plus className="w-3.5 h-3.5 stroke-[2]" />
                      )}
                    </div>
                  </button>
                </h3>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={`faq-answer-${idx}`}
                      role="region"
                      aria-labelledby={`faq-btn-${idx}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22, ease: "easeInOut" }}
                    >
                      <div className="pt-3 pb-2 pr-6 sm:pr-8">
                        <p className="font-body text-[14px] text-[#626262] leading-relaxed">
                          {item.a}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </Section>
  );
}
