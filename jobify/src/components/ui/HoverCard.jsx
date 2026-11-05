import React from "react";
import { cn } from "../../lib/utils.js";

/**
 * HoverCard: Aceternity-style card container with subtle hover-lift elevation
 * and interactive focus transitions.
 */
export default function HoverCard({
  children,
  className = "",
  elevation = "default", // "default" | "high"
  ...props
}) {
  const liftClasses =
    elevation === "high"
      ? "hover:-translate-y-1.5 hover:shadow-[0_16px_36px_rgba(20,30,20,0.12)]"
      : "hover:-translate-y-1 hover:shadow-[0_10px_28px_rgba(20,30,20,0.08)]";

  return (
    <div
      className={cn(
        "transition-all duration-300 ease-out will-change-transform",
        liftClasses,
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
