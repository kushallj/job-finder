import React from "react";
import { Link } from "react-router-dom";
import { cn } from "../lib/utils.js";

/**
 * Jobify Brand Logo Component
 * Clean geometric monogram paired with Bricolage Grotesque wordmark.
 */
export default function Logo({
  variant = "nav", // "nav" | "footer"
  className = "",
  showWordmark = true,
  onClick,
}) {
  const isFooter = variant === "footer";
  const iconSize = isFooter ? 34 : 26;

  return (
    <Link
      to="/"
      onClick={onClick}
      aria-label="Jobify Home"
      className={cn(
        "inline-flex items-center gap-2.5 select-none text-[#161616] transition-opacity hover:opacity-90 focus-visible:rounded-md",
        className
      )}
    >
      {/* Sleek Jobify Geometric Monogram */}
      <div
        style={{ width: iconSize, height: iconSize }}
        className="rounded-lg bg-[#141414] text-white flex items-center justify-center shrink-0 shadow-xs"
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="w-4 h-4"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Stylized J with upward career arrow */}
          <path d="M12 4v10a4 4 0 0 1-8 0" />
          <path d="M12 4l3 3" />
          <path d="M12 4l-3 3" />
          <circle cx="18" cy="7" r="1.5" fill="currentColor" stroke="none" />
        </svg>
      </div>

      {showWordmark && (
        <span
          className={cn(
            "font-display font-bold text-[#161616] leading-none tracking-tight",
            isFooter ? "wordmark-footer" : "wordmark-nav"
          )}
        >
          Jobify
        </span>
      )}
    </Link>
  );
}
