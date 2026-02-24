import type { Metadata } from "next";
import ProcessForm from "./ProcessForm";

export const metadata: Metadata = {
  title: "Analyze a Bill",
  description: "Enter a bill number to analyze it with PorkChop.",
};

export default function ProcessPage() {
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold mb-2">Analyze a Bill</h1>
      <p className="text-text-dim text-sm mb-6">
        Enter any bill number. PorkChop will fetch it from Congress.gov,
        extract spending data, and score it for pork — all in under a minute.
      </p>
      <ProcessForm />
    </div>
  );
}
