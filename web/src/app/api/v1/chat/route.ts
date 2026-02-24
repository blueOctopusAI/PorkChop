import { NextRequest, NextResponse } from "next/server";
import {
  getBill,
  getSpending,
  getTotalSpending,
  getDeadlines,
  getEntities,
  getReferences,
  getBillSummary,
  getPorkSummary,
  getPorkScores,
} from "@/lib/db";
import { chatCompletion, type Provider, type Message } from "@/lib/llm";

const SYSTEM_PROMPT = `You are PorkChop, an AI assistant that helps people understand congressional bills. You have access to structured data extracted from the bill text.

Answer questions based on the bill data provided. Be specific — cite exact dollar amounts, entity names, and dates from the data. If the data doesn't contain the answer, say so rather than guessing.

Keep answers concise but thorough. Use plain English — no legal jargon.`;

function buildContext(billId: number): string {
  const bill = getBill(billId);
  if (!bill) return "Bill not found.";

  const spending = getSpending(billId);
  const total = getTotalSpending(billId);
  const deadlines = getDeadlines(billId);
  const entities = getEntities(billId);
  const refs = getReferences(billId);
  const summary = getBillSummary(billId);
  const pork = getPorkSummary(billId);
  const scores = getPorkScores(billId);

  let ctx = `## Bill: ${bill.title || "Untitled"}\n`;
  ctx += `${bill.congress}th Congress — ${bill.bill_type.toUpperCase()} ${bill.bill_number}\n`;
  if (bill.status) ctx += `Status: ${bill.status}\n`;
  ctx += `\n`;

  if (summary) {
    ctx += `## Summary\n${summary}\n\n`;
  }

  ctx += `## Spending Overview\n`;
  ctx += `Total: $${total.toLocaleString()} across ${spending.length} items\n`;
  if (pork.scored_items > 0) {
    ctx += `Pork Score: avg ${pork.avg_score?.toFixed(0) || "N/A"}/100, highest ${pork.max_score || 0}/100, ${pork.high_pork_count} high-pork items\n`;
  }
  ctx += `\n`;

  // Top 30 spending items
  ctx += `## Top Spending Items\n`;
  spending.slice(0, 30).forEach((s, i) => {
    ctx += `${i + 1}. ${s.amount} — ${s.purpose || "unspecified"}`;
    if (s.recipient) ctx += ` (${s.recipient})`;
    if (s.availability) ctx += ` [${s.availability}]`;
    ctx += `\n`;
  });
  if (spending.length > 30) ctx += `... and ${spending.length - 30} more items\n`;
  ctx += `\n`;

  // High pork items
  const highPork = scores.filter((s) => s.score >= 30);
  if (highPork.length > 0) {
    ctx += `## Notable Pork Scores\n`;
    highPork.slice(0, 15).forEach((s) => {
      ctx += `- Score ${s.score}/100: ${s.amount || "?"} — ${s.purpose || "unspecified"}\n`;
    });
    ctx += `\n`;
  }

  // Deadlines
  if (deadlines.length > 0) {
    ctx += `## Deadlines (${deadlines.length} total)\n`;
    deadlines.slice(0, 20).forEach((d) => {
      ctx += `- ${d.date || "?"}: ${d.action || "?"}\n`;
    });
    ctx += `\n`;
  }

  // Entities
  if (entities.length > 0) {
    ctx += `## Entities (${entities.length} total)\n`;
    ctx += entities.map((e) => e.name).join(", ") + "\n\n";
  }

  // Legal references summary
  if (refs.length > 0) {
    ctx += `## Legal References: ${refs.length} total\n`;
  }

  return ctx;
}

export async function POST(req: NextRequest) {
  try {
    const { billId, question, provider, apiKey, model } = await req.json();

    if (!billId || !question) {
      return NextResponse.json(
        { error: "billId and question are required" },
        { status: 400 }
      );
    }

    if (!provider || !apiKey) {
      return NextResponse.json(
        { error: "AI provider and API key are required for chat" },
        { status: 400 }
      );
    }

    const bill = getBill(Number(billId));
    if (!bill) {
      return NextResponse.json(
        { error: "Bill not found" },
        { status: 404 }
      );
    }

    const context = buildContext(Number(billId));

    const messages: Message[] = [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `Here is the structured data for ${bill.title || "this bill"}:\n\n${context}\n\n---\n\nUser question: ${question}`,
      },
    ];

    const response = await chatCompletion(
      { provider: provider as Provider, apiKey, model },
      messages
    );

    return NextResponse.json({ answer: response });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Chat failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
