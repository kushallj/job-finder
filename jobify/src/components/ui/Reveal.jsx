import React from "react";
import { useReveal } from "../../hooks/useReveal.js";
import { cn } from "../../lib/utils.js";

/**
 * Reveal: Progressive enhancement wrapper for graceful section fade-up
 */
export default function Reveal({
  children,
  className = "",
  threshold = 0.15,
  as: Component = "div",
  ...props
}) {
  const [ref, isRevealed] = useReveal(threshold);

  return (
    <Component
      ref={ref}
      className={cn("reveal-init", isRevealed && "reveal-active", className)}
      {...props}
    >
      {children}
    </Component>
  );
}
