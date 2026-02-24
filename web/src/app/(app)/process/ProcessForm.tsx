"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loadSettings } from "@/lib/settings";
import { Settings } from "lucide-react";
import SettingsModal from "@/components/SettingsModal";

type Status = "idle" | "processing" | "done" | "error";

export default function ProcessForm() {
  const router = useRouter();
  const [billId, setBillId] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [resultId, setResultId] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    setHasKey(loadSettings().congressApiKey.length > 0);
  }, [showSettings]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!billId.trim()) return;

    setStatus("processing");
    setMessage("Fetching bill from Congress.gov...");

    try {
      const settings = loadSettings();
      const resp = await fetch("/api/v1/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          billId: billId.trim(),
          congressApiKey: settings.congressApiKey || undefined,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        setStatus("error");
        setMessage(data.error || "Processing failed");
        return;
      }

      setStatus("done");
      setMessage(data.message);
      setResultId(data.billDbId);

      if (data.status === "cached") {
        setMessage("This bill is already in the database.");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Is the server running?");
    }
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Bill Number
          </label>
          <input
            type="text"
            value={billId}
            onChange={(e) => setBillId(e.target.value)}
            placeholder="HR-10515, S-1234, 118-hr-10515..."
            className="w-full bg-bg border border-border rounded-lg px-4 py-3 text-lg font-mono focus:border-accent focus:outline-none"
            disabled={status === "processing"}
          />
          <p className="text-xs text-text-dim mt-1">
            Enter a bill ID in any format: HR-10515, HR 10515, 118-hr-10515
          </p>
        </div>

        {!hasKey && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 flex items-start gap-3">
            <span className="text-amber-500 text-sm">
              You need a Congress.gov API key to fetch bills.{" "}
              <button
                type="button"
                onClick={() => setShowSettings(true)}
                className="text-accent hover:underline inline-flex items-center gap-1"
              >
                <Settings className="w-3 h-3" /> Add it in Settings
              </button>
            </span>
          </div>
        )}

        <button
          type="submit"
          disabled={status === "processing" || !billId.trim()}
          className="bg-accent text-bg px-6 py-3 rounded-lg font-semibold hover:bg-accent-dim hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full"
        >
          {status === "processing" ? "Processing..." : "Analyze Bill"}
        </button>

        {message && (
          <div
            className={`rounded-lg p-4 text-sm ${
              status === "error"
                ? "bg-red-500/10 border border-red-500/30 text-red-400"
                : status === "done"
                  ? "bg-green-500/10 border border-green-500/30 text-green-400"
                  : "bg-surface border border-border text-text-dim"
            }`}
          >
            {message}
          </div>
        )}

        {resultId && (
          <button
            type="button"
            onClick={() => router.push(`/bills/${resultId}`)}
            className="border border-accent text-accent px-6 py-3 rounded-lg font-semibold hover:bg-accent hover:text-bg transition-colors w-full"
          >
            View Bill Analysis
          </button>
        )}
      </form>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* How it works */}
      <div className="mt-8 bg-surface border border-border rounded-lg p-5">
        <h3 className="font-semibold mb-3">What happens when you analyze a bill</h3>
        <ol className="text-sm text-text-dim space-y-2">
          <li className="flex gap-2">
            <span className="text-accent font-mono">1.</span>
            <span>Bill text and metadata are fetched from Congress.gov</span>
          </li>
          <li className="flex gap-2">
            <span className="text-accent font-mono">2.</span>
            <span>Text is cleaned, chunked, and structured</span>
          </li>
          <li className="flex gap-2">
            <span className="text-accent font-mono">3.</span>
            <span>
              Dollar amounts, legal references, deadlines, and entities are extracted
            </span>
          </li>
          <li className="flex gap-2">
            <span className="text-accent font-mono">4.</span>
            <span>Every spending item is scored for pork likelihood</span>
          </li>
          <li className="flex gap-2">
            <span className="text-accent font-mono">5.</span>
            <span>
              Results are cached — future visitors see them instantly
            </span>
          </li>
        </ol>
        <p className="text-xs text-text-dim mt-3">
          Steps 1-5 use regex extraction (free, fast). For AI-powered summaries
          and deeper analysis, configure your AI provider in Settings.
        </p>
      </div>
    </>
  );
}
