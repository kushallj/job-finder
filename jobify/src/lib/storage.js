import { useEffect, useState } from "react";

const PREFIX = "jobify:";

export function readStore(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function writeStore(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* storage unavailable: demo state just won't persist */
  }
}

/** useState that persists to localStorage (demo persistence only). */
export function usePersisted(key, initial) {
  const [value, setValue] = useState(() => readStore(key, initial));
  useEffect(() => writeStore(key, value), [key, value]);
  return [value, setValue];
}

export const wait = (ms = 350) => new Promise((r) => setTimeout(r, ms));
export const uid = (p = "id") => `${p}_${Math.random().toString(36).slice(2, 9)}`;
