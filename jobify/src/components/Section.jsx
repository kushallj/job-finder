import React from "react";
import { cn } from "../lib/utils.js";

/**
 * Standard semantic section container adhering to Jobify design tokens.
 * Enforces fluid container gutters and section block padding.
 */
export default function Section({
  as: Component = "section",
  id,
  className = "",
  containerClassName = "",
  fullWidth = false,
  children,
  ...props
}) {
  return (
    <Component
      id={id}
      className={cn("w-full relative scroll-mt-24", className)}
      {...props}
    >
      {fullWidth ? (
        children
      ) : (
        <div
          className={cn(
            "mx-auto w-full max-w-[1240px] px-5 sm:px-8 lg:px-12",
            containerClassName
          )}
        >
          {children}
        </div>
      )}
    </Component>
  );
}
