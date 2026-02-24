"use client";

import { useState } from "react";
import { truncate, cleanAmount } from "@/lib/format";
import { getPorkBadgeClass } from "@/lib/pork-colors";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { SpendingItem, PorkScore } from "@/lib/types";

export default function SpendingRow({
  item,
  pork,
  hasPorkScores,
}: {
  item: SpendingItem;
  pork?: PorkScore;
  hasPorkScores: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const rowBg = pork
    ? pork.score >= 60
      ? "bg-red-500/5"
      : pork.score >= 30
        ? "bg-amber-500/5"
        : ""
    : "";

  return (
    <>
      <tr
        className={`border-b border-border last:border-0 hover:bg-surface-hover cursor-pointer ${rowBg}`}
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-2.5 text-text-dim w-8">
          {item.source_text ? (
            expanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )
          ) : null}
        </td>
        <td className="px-4 py-2.5 font-mono text-sm text-accent whitespace-nowrap">
          {cleanAmount(item.amount)}
        </td>
        <td className="px-4 py-2.5 text-sm max-w-md">
          {truncate(item.purpose || "—", 100)}
        </td>
        <td className="px-4 py-2.5 text-sm text-text-dim">
          {truncate(item.recipient || "—", 50)}
        </td>
        <td className="px-4 py-2.5 text-sm text-text-dim">
          {item.availability || "—"}
        </td>
        {hasPorkScores && (
          <td className="px-4 py-2.5 text-center">
            {pork ? (
              <span
                className={`inline-block text-xs font-bold px-2 py-0.5 rounded ${getPorkBadgeClass(pork.score)}`}
              >
                {pork.score}
              </span>
            ) : (
              <span className="text-text-dim text-xs">—</span>
            )}
          </td>
        )}
      </tr>
      {expanded && item.source_text && (
        <tr className="border-b border-border bg-bg/50">
          <td
            colSpan={hasPorkScores ? 6 : 5}
            className="px-4 py-3"
          >
            <div className="text-xs text-text-dim">
              <span className="font-semibold text-text-dim uppercase tracking-wider">
                Source text:
              </span>
              <p className="mt-1 font-mono leading-relaxed whitespace-pre-wrap bg-surface border border-border rounded p-3">
                {item.source_text}
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
