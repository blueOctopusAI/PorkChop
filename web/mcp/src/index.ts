#!/usr/bin/env node

/**
 * PorkChop MCP Server
 *
 * Provides LLM-friendly access to PorkChop bill analysis data.
 * Reads the same SQLite database as the web UI.
 *
 * Usage:
 *   node dist/index.js --db /path/to/porkchop.db
 *
 * Claude Desktop config:
 *   {
 *     "mcpServers": {
 *       "porkchop": {
 *         "command": "node",
 *         "args": ["path/to/web/mcp/dist/index.js", "--db", "path/to/data/porkchop.db"]
 *       }
 *     }
 *   }
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  initDb,
  listBills,
  getBill,
  searchBills,
  getSpending,
  getTotalSpending,
  getPorkScores,
  getPorkSummary,
  getDeadlines,
  getEntities,
  getReferences,
  getBillSummary,
  getVersions,
  getComparison,
  getStats,
} from "./db.js";

// Parse --db argument
const args = process.argv.slice(2);
const dbIdx = args.indexOf("--db");
const dbPath = dbIdx >= 0 && args[dbIdx + 1] ? args[dbIdx + 1] : undefined;

if (!dbPath) {
  console.error("Usage: porkchop-mcp --db /path/to/porkchop.db");
  process.exit(1);
}

initDb(dbPath);

const server = new McpServer({
  name: "porkchop",
  version: "1.0.0",
});

// --- Tools ---

server.tool(
  "list_bills",
  "List all analyzed bills in the database",
  { limit: z.number().optional().describe("Maximum number of bills to return (default 50)") },
  async ({ limit }) => ({
    content: [{ type: "text", text: JSON.stringify(listBills(limit ?? 50), null, 2) }],
  })
);

server.tool(
  "get_bill",
  "Get metadata for a specific bill by its database ID",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => {
    const bill = getBill(bill_id);
    if (!bill) return { content: [{ type: "text", text: `Bill ${bill_id} not found` }] };
    const summary = getBillSummary(bill_id);
    return {
      content: [{ type: "text", text: JSON.stringify({ ...bill as object, ai_summary: summary }, null, 2) }],
    };
  }
);

server.tool(
  "search_bills",
  "Search analyzed bills by keyword (searches title, short title, and summary)",
  { query: z.string().describe("Search term") },
  async ({ query }) => ({
    content: [{ type: "text", text: JSON.stringify(searchBills(query), null, 2) }],
  })
);

server.tool(
  "get_spending",
  "Get all spending items for a bill, sorted by amount descending",
  {
    bill_id: z.number().describe("The bill's database ID"),
    min_pork: z.number().optional().describe("Minimum pork score filter"),
  },
  async ({ bill_id, min_pork }) => {
    const spending = getSpending(bill_id);
    const total = getTotalSpending(bill_id);
    let items = spending as Record<string, unknown>[];
    if (min_pork !== undefined) {
      const porkScores = getPorkScores(bill_id) as Record<string, unknown>[];
      const porkMap = new Map(porkScores.map((s) => [s.spending_item_id, s]));
      items = (spending as Record<string, unknown>[]).filter((s) => {
        const pork = porkMap.get(s.id) as Record<string, unknown> | undefined;
        return pork && (pork.score as number) >= min_pork;
      });
    }
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ total, count: items.length, spending: items }, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "get_pork_scores",
  "Get pork scores for all spending items in a bill, sorted by score descending",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => ({
    content: [{ type: "text", text: JSON.stringify(getPorkScores(bill_id), null, 2) }],
  })
);

server.tool(
  "get_pork_summary",
  "Get aggregate pork statistics for a bill (average, max, high-pork count)",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => ({
    content: [{ type: "text", text: JSON.stringify(getPorkSummary(bill_id), null, 2) }],
  })
);

server.tool(
  "get_deadlines",
  "Get all deadlines in a bill with responsible entities and required actions",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => ({
    content: [{ type: "text", text: JSON.stringify(getDeadlines(bill_id), null, 2) }],
  })
);

server.tool(
  "get_entities",
  "Get all government entities (departments, agencies, offices) mentioned in a bill",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => ({
    content: [{ type: "text", text: JSON.stringify(getEntities(bill_id), null, 2) }],
  })
);

server.tool(
  "get_references",
  "Get legal references (US Code, Public Laws, Acts) in a bill",
  {
    bill_id: z.number().describe("The bill's database ID"),
    ref_type: z.string().optional().describe("Filter by type: us_code, public_law, or act"),
  },
  async ({ bill_id, ref_type }) => ({
    content: [{ type: "text", text: JSON.stringify(getReferences(bill_id, ref_type), null, 2) }],
  })
);

server.tool(
  "get_bill_summary",
  "Get the AI-generated plain English summary for a bill",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => {
    const summary = getBillSummary(bill_id);
    return {
      content: [{ type: "text", text: summary || "No summary available. Run: porkchop analyze " + bill_id }],
    };
  }
);

server.tool(
  "get_versions",
  "List all versions of a bill (Introduced, Committee, Enrolled, etc.)",
  { bill_id: z.number().describe("The bill's database ID") },
  async ({ bill_id }) => ({
    content: [{ type: "text", text: JSON.stringify(getVersions(bill_id), null, 2) }],
  })
);

server.tool(
  "compare_versions",
  "Get the comparison between two versions of a bill",
  {
    bill_id: z.number().describe("The bill's database ID"),
    from_version: z.number().describe("Source version ID"),
    to_version: z.number().describe("Target version ID"),
  },
  async ({ bill_id, from_version, to_version }) => {
    const comparison = getComparison(bill_id, from_version, to_version);
    if (!comparison) {
      return { content: [{ type: "text", text: "No comparison found. Run: porkchop compare " + bill_id }] };
    }
    return { content: [{ type: "text", text: JSON.stringify(comparison, null, 2) }] };
  }
);

server.tool(
  "get_stats",
  "Get aggregate database statistics (bills analyzed, spending items, total spending, items scored)",
  {},
  async () => ({
    content: [{ type: "text", text: JSON.stringify(getStats(), null, 2) }],
  })
);

// --- Start ---

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("MCP server error:", err);
  process.exit(1);
});
