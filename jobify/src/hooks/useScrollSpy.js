import { useState, useEffect } from "react";

/**
 * Hook to observe active section for header nav highlighting.
 * @param {string[]} sectionIds - Array of section DOM IDs
 * @param {number} offset - Pixel offset from top
 */
export function useScrollSpy(sectionIds = [], offset = 120) {
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    if (typeof window === "undefined" || sectionIds.length === 0) return;

    const handleScroll = () => {
      const scrollPosition = window.scrollY + offset;

      // Special check: at very top of document
      if (window.scrollY < 100) {
        setActiveId("top");
        return;
      }

      let currentActive = "";
      for (let i = 0; i < sectionIds.length; i++) {
        const id = sectionIds[i];
        const el = document.getElementById(id);
        if (el) {
          const top = el.offsetTop;
          const height = el.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            currentActive = id;
            break;
          }
        }
      }

      if (currentActive) {
        setActiveId(currentActive);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => window.removeEventListener("scroll", handleScroll);
  }, [sectionIds, offset]);

  return activeId;
}
