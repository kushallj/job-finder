import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Robust Storage mock class
class MockStorage implements Storage {
  private store: Record<string, string> = {};

  getItem(key: string): string | null {
    return this.store[key] ?? null;
  }
  setItem(key: string, value: string): void {
    this.store[key] = String(value);
  }
  removeItem(key: string): void {
    delete this.store[key];
  }
  clear(): void {
    this.store = {};
  }
  get length(): number {
    return Object.keys(this.store).length;
  }
  key(index: number): string | null {
    return Object.keys(this.store)[index] ?? null;
  }
}

const mockLocalStorage = new MockStorage();
const mockSessionStorage = new MockStorage();

Object.defineProperty(globalThis, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
  configurable: true,
});
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
  configurable: true,
});

Object.defineProperty(globalThis, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true,
  configurable: true,
});
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true,
  configurable: true,
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockLocalStorage.clear();
  mockSessionStorage.clear();
});

// Polyfill window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Polyfill window.scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn(),
});

// Polyfill ResizeObserver
(globalThis as unknown as Record<string, unknown>).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Polyfill IntersectionObserver
(globalThis as unknown as Record<string, unknown>).IntersectionObserver = class IntersectionObserver {

  readonly root: Element | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
} as unknown as typeof IntersectionObserver;

// Polyfill navigator.clipboard
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue(''),
  },
});

// Polyfill scrollIntoView in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();
window.Element.prototype.scrollIntoView = vi.fn();

// Polyfill Recharts ResponsiveContainer in jsdom

vi.mock('recharts', async () => {
  const original = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => children ?? null,
  };
});

