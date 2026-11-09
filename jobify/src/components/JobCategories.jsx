import React, { useState } from "react";
import {
  Bot,
  Code,
  Server,
  Layers,
  Layout,
  BarChart3,
  Binary,
  Cpu,
  Smartphone,
  Megaphone,
  CheckSquare,
  GraduationCap,
  Globe,
  Briefcase,
  Check,
} from "lucide-react";
import Section from "./Section.jsx";
import Reveal from "./ui/Reveal.jsx";
import { SITE_CONTENT } from "../data/siteContent.js";
import { cn } from "../lib/utils.js";

const categoryIconMap = {
  Bot: Bot,
  Code: Code,
  Server: Server,
  Layers: Layers,
  Figma: Layout,
  Layout: Layout,
  BarChart3: BarChart3,
  Binary: Binary,
  Cpu: Cpu,
  Smartphone: Smartphone,
  Megaphone: Megaphone,
  CheckSquare: CheckSquare,
  GraduationCap: GraduationCap,
  Globe: Globe,
};

export default function JobCategories() {
  const { categories } = SITE_CONTENT;
  const [selectedCategory, setSelectedCategory] = useState("frontend");

  return (
    <Section id="categories" className="py-16 md:py-24 bg-[#FAFAFA] border-y border-[#F0F0F0]">
      <div className="mx-auto max-w-[820px] text-center">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#E8E8E8] text-[11.5px] font-body font-medium text-[#626262] tracking-wider uppercase mb-4">
          <Briefcase className="w-3 h-3 text-[#161616]" />
          <span>{categories.eyebrow}</span>
        </div>

        {/* Heading */}
        <Reveal>
          <h2 className="font-display text-section-h2 text-[#161616] tracking-tight">
            {categories.heading}
          </h2>
          <p className="mt-3.5 mx-auto max-w-[480px] font-body text-[15px] sm:text-[16px] text-[#626262] leading-relaxed">
            {categories.description}
          </p>
        </Reveal>
      </div>

      {/* Category Chips Container */}
      <div className="mt-10 md:mt-12 mx-auto max-w-[960px] flex flex-wrap items-center justify-center gap-2.5 sm:gap-3">
        {categories.chips.map((chip) => {
          const Icon = categoryIconMap[chip.icon] || Briefcase;
          const isSelected = selectedCategory === chip.id;

          return (
            <button
              key={chip.id}
              type="button"
              onClick={() => setSelectedCategory(chip.id)}
              className={cn(
                "group inline-flex items-center gap-2 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full text-[13.5px] sm:text-[14px] font-body font-medium transition-all duration-150 border cursor-pointer focus-visible:rounded-full",
                isSelected
                  ? "bg-[#141414] text-white border-[#141414] shadow-xs"
                  : "bg-white text-[#161616] border-[#E8E8E8] hover:border-[#CCCCCC] hover:bg-[#F9F9F9]"
              )}
              aria-pressed={isSelected}
            >
              <Icon
                className={cn(
                  "w-3.5 h-3.5 transition-colors",
                  isSelected ? "text-white" : "text-[#626262] group-hover:text-[#161616]"
                )}
              />
              <span>{chip.label}</span>
              {isSelected && <Check className="w-3 h-3 text-white ml-0.5" />}
            </button>
          );
        })}
      </div>

      {/* Dynamic filter feedback indicator */}
      <div className="mt-6 text-center">
        <span className="text-[12px] font-body text-[#888888]">
          Selected: <strong className="text-[#161616] font-medium">{categories.chips.find((c) => c.id === selectedCategory)?.label}</strong> —{" "}
          {categories.chips.find((c) => c.id === selectedCategory)?.count} currently tracked
        </span>
      </div>
    </Section>
  );
}
