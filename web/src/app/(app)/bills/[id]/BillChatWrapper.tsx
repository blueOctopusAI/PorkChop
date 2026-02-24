"use client";

import BillChat from "@/components/BillChat";

export default function BillChatWrapper({ billId }: { billId: number }) {
  return <BillChat billId={billId} />;
}
