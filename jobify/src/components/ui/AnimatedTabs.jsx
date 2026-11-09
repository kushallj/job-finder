import React, { useRef } from "react";
import { motion } from "motion/react";
import { cn } from "../../lib/utils.js";

/**
 * AnimatedTabs: Aceternity-style tab list with animated sliding baseline indicator
 * and full ARIA keyboard navigation support (Left/Right/Home/End).
 */
export default function AnimatedTabs({
  tabs = [],
  activeTab,
  onTabChange,
  className = "",
}) {
  const tabRefs = useRef([]);

  const handleKeyDown = (e, index) => {
    let nextIndex = null;
    if (e.key === "ArrowRight") {
      nextIndex = (index + 1) % tabs.length;
    } else if (e.key === "ArrowLeft") {
      nextIndex = (index - 1 + tabs.length) % tabs.length;
    } else if (e.key === "Home") {
      nextIndex = 0;
    } else if (e.key === "End") {
      nextIndex = tabs.length - 1;
    }

    if (nextIndex !== null) {
      e.preventDefault();
      onTabChange(tabs[nextIndex].id);
      tabRefs.current[nextIndex]?.focus();
    }
  };

  return (
    <div
      role="tablist"
      aria-label="FAQ categories"
      className={cn("relative flex items-center justify-center border-b border-[#E6E6E6]", className)}
    >
      <div className="flex gap-4 sm:gap-8">
        {tabs.map((tab, idx) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              ref={(el) => (tabRefs.current[idx] = el)}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onTabChange(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, idx)}
              className={cn(
                "relative pb-3 pt-2 text-[14px] sm:text-[15px] font-medium transition-colors focus-visible:rounded-sm",
                isActive ? "text-[#1C1C1C]" : "text-[#8A8A8A] hover:text-[#5C5C5C]"
              )}
            >
              <span className="flex items-center gap-2">
                {tab.icon}
                <span>{tab.label}</span>
              </span>

              {/* Animated Sliding Underline Indicator */}
              {isActive && (
                <motion.div
                  layoutId="active-tab-indicator"
                  className="absolute bottom-0 inset-x-0 h-[2px] bg-[#1C1C1C]"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
