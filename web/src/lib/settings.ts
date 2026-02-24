/**
 * Client-side settings stored in localStorage.
 * API keys never touch server storage — only sent per-request.
 */

import type { Provider } from "./llm";

export interface UserSettings {
  congressApiKey: string;
  aiProvider: Provider;
  aiApiKey: string;
  aiModel: string;
}

const STORAGE_KEY = "porkchop-settings";

const DEFAULTS: UserSettings = {
  congressApiKey: "",
  aiProvider: "anthropic",
  aiApiKey: "",
  aiModel: "",
};

export function loadSettings(): UserSettings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

export function saveSettings(settings: UserSettings): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function hasCongressKey(): boolean {
  return loadSettings().congressApiKey.length > 0;
}

export function hasAiKey(): boolean {
  const s = loadSettings();
  return s.aiApiKey.length > 0;
}
