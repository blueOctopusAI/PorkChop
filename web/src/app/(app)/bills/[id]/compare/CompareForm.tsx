"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { BillVersion } from "@/lib/types";

export default function CompareForm({
  billId,
  versions,
  fromId,
  toId,
}: {
  billId: number;
  versions: BillVersion[];
  fromId?: number;
  toId?: number;
}) {
  const router = useRouter();
  const [from, setFrom] = useState(fromId?.toString() || "");
  const [to, setTo] = useState(toId?.toString() || "");

  function handleCompare() {
    if (from && to) {
      router.push(`/bills/${billId}/compare?from=${from}&to=${to}`);
    }
  }

  return (
    <div className="flex items-end gap-4">
      <div>
        <label className="block text-xs text-text-dim mb-1">From</label>
        <select
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="bg-bg border border-border text-text px-3 py-2 rounded-lg text-sm"
        >
          <option value="">Select version</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.version_code} {v.version_name ? `— ${v.version_name}` : ""}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-text-dim mb-1">To</label>
        <select
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="bg-bg border border-border text-text px-3 py-2 rounded-lg text-sm"
        >
          <option value="">Select version</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              {v.version_code} {v.version_name ? `— ${v.version_name}` : ""}
            </option>
          ))}
        </select>
      </div>
      <button
        onClick={handleCompare}
        disabled={!from || !to}
        className="bg-accent text-bg px-4 py-2 rounded-lg text-sm font-semibold hover:bg-accent-dim hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Compare
      </button>
    </div>
  );
}
