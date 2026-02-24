/** Pork score color system — green (clean) / amber (watch) / red (pork) */

export type PorkLevel = "low" | "med" | "high";

export function getPorkLevel(score: number): PorkLevel {
  if (score >= 60) return "high";
  if (score >= 30) return "med";
  return "low";
}

export function getPorkLabel(score: number): string {
  if (score >= 60) return "Pork";
  if (score >= 30) return "Watch";
  return "Clean";
}

export function getPorkColor(score: number): string {
  if (score >= 60) return "#ef4444";
  if (score >= 30) return "#f59e0b";
  return "#22c55e";
}

export function getPorkBgClass(score: number): string {
  if (score >= 60) return "bg-red-500/15 text-red-400";
  if (score >= 30) return "bg-amber-500/15 text-amber-400";
  return "bg-green-500/15 text-green-400";
}

export function getPorkBadgeClass(score: number): string {
  if (score >= 60) return "bg-red-500 text-white";
  if (score >= 30) return "bg-amber-500 text-black";
  return "bg-green-500 text-black";
}
