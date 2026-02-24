/** Formatting utilities */

/** Strip trailing commas/whitespace from raw extracted amounts */
export function cleanAmount(amount: string): string {
  return amount.replace(/,\s*$/, "");
}

export function formatCurrency(amount: number): string {
  if (amount >= 1_000_000_000) {
    return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  }
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `$${(amount / 1_000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

export function formatCurrencyFull(amount: number): string {
  return `$${amount.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatBillId(bill: {
  congress: number;
  bill_type: string;
  bill_number: number;
}): string {
  return `${bill.bill_type.toUpperCase()} ${bill.bill_number}`;
}

export function formatBillIdFull(bill: {
  congress: number;
  bill_type: string;
  bill_number: number;
}): string {
  return `${bill.congress}th Congress — ${bill.bill_type.toUpperCase()} ${bill.bill_number}`;
}

export function truncate(str: string, len: number): string {
  if (str.length <= len) return str;
  return str.slice(0, len) + "...";
}
