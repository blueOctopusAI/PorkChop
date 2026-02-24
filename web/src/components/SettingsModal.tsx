"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import type { UserSettings } from "@/lib/settings";
import { loadSettings, saveSettings } from "@/lib/settings";
import type { Provider } from "@/lib/llm";
import { getProviderLabel, getModelOptions } from "@/lib/llm";

const PROVIDERS: Provider[] = ["anthropic", "openai", "xai"];

export default function SettingsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [settings, setSettings] = useState<UserSettings>(loadSettings());

  useEffect(() => {
    if (open) setSettings(loadSettings());
  }, [open]);

  if (!open) return null;

  function handleSave() {
    saveSettings(settings);
    onClose();
  }

  const models = getModelOptions(settings.aiProvider);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-surface border border-border rounded-lg w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Settings</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-5">
          {/* Congress API Key */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Congress.gov API Key
            </label>
            <input
              type="password"
              value={settings.congressApiKey}
              onChange={(e) =>
                setSettings({ ...settings, congressApiKey: e.target.value })
              }
              placeholder="Your api.data.gov key"
              className="w-full bg-bg border border-border rounded px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
            <p className="text-xs text-text-dim mt-1">
              Free at{" "}
              <a
                href="https://api.data.gov/signup/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline"
              >
                api.data.gov/signup
              </a>
              . Required to fetch new bills.
            </p>
          </div>

          {/* AI Provider */}
          <div>
            <label className="block text-sm font-medium mb-1">
              AI Provider
            </label>
            <select
              value={settings.aiProvider}
              onChange={(e) => {
                const provider = e.target.value as Provider;
                setSettings({
                  ...settings,
                  aiProvider: provider,
                  aiModel: "",
                });
              }}
              className="w-full bg-bg border border-border rounded px-3 py-2 text-sm focus:border-accent focus:outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {getProviderLabel(p)}
                </option>
              ))}
            </select>
            <p className="text-xs text-text-dim mt-1">
              Used for AI summaries, pork scoring, and chat. You pay your own
              usage.
            </p>
          </div>

          {/* AI API Key */}
          <div>
            <label className="block text-sm font-medium mb-1">
              AI API Key
            </label>
            <input
              type="password"
              value={settings.aiApiKey}
              onChange={(e) =>
                setSettings({ ...settings, aiApiKey: e.target.value })
              }
              placeholder={`Your ${getProviderLabel(settings.aiProvider)} key`}
              className="w-full bg-bg border border-border rounded px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <select
              value={settings.aiModel || models[0]}
              onChange={(e) =>
                setSettings({ ...settings, aiModel: e.target.value })
              }
              className="w-full bg-bg border border-border rounded px-3 py-2 text-sm focus:border-accent focus:outline-none"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-dim hover:text-text"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="bg-accent text-bg px-4 py-2 rounded text-sm font-semibold hover:bg-accent-dim hover:text-white transition-colors"
          >
            Save
          </button>
        </div>

        <p className="text-xs text-text-dim mt-4 text-center">
          Keys are stored in your browser only. Never sent to our servers.
        </p>
      </div>
    </div>
  );
}
