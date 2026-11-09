import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combines conditional classes and merges conflicting Tailwind classes.
 * @param {...any} inputs - Class names, conditionals, objects, or arrays.
 * @returns {string} Merged class names string.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
