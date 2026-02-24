import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import { writeFileSync, mkdtempSync, unlinkSync, rmdirSync } from "fs";
import path from "path";
import os from "os";
import Database from "better-sqlite3";
import { DB_PATH } from "@/lib/config";

const execAsync = promisify(exec);

const PROJECT_ROOT = path.resolve(process.cwd(), "..");

export async function POST(req: NextRequest) {
  try {
    const { billId, congressApiKey } = await req.json();

    if (!billId) {
      return NextResponse.json(
        { error: "billId is required (e.g., HR-10515)" },
        { status: 400 }
      );
    }

    // Check if bill already exists in DB
    const db = new Database(DB_PATH, { readonly: true });
    const existing = db
      .prepare(
        "SELECT id, title FROM bills WHERE bill_type || '-' || bill_number = ? OR bill_type || bill_number = ?"
      )
      .get(billId.toLowerCase().replace(/[\s-]/g, ""), billId.toLowerCase().replace(/[\s-]/g, "")) as
      | { id: number; title: string }
      | undefined;
    db.close();

    if (existing) {
      return NextResponse.json({
        status: "cached",
        billDbId: existing.id,
        title: existing.title,
        message: "Bill already processed. View it now.",
      });
    }

    // Build env for subprocess — use provided key or server env
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      PYTHONPATH: path.join(PROJECT_ROOT, "src"),
    };

    const apiKey = congressApiKey || process.env.CONGRESS_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        {
          error:
            "Congress.gov API key required. Get one free at https://api.data.gov/signup/",
        },
        { status: 400 }
      );
    }
    env.CONGRESS_API_KEY = apiKey;

    // Step 1: Fetch bill metadata + text
    const sanitizedId = billId.replace(/[^a-zA-Z0-9-]/g, "");
    await execAsync(
      `python3 -m porkchop.cli fetch ${sanitizedId} --text`,
      { env, cwd: PROJECT_ROOT, timeout: 60000 }
    );

    // Step 2: Get the bill's raw text from DB
    const dbWrite = new Database(DB_PATH);
    const bill = dbWrite
      .prepare("SELECT id, title FROM bills ORDER BY id DESC LIMIT 1")
      .get() as { id: number; title: string } | undefined;

    if (!bill) {
      dbWrite.close();
      return NextResponse.json(
        { error: "Failed to fetch bill" },
        { status: 500 }
      );
    }

    const version = dbWrite
      .prepare(
        "SELECT raw_text FROM bill_versions WHERE bill_id = ? AND raw_text IS NOT NULL ORDER BY id DESC LIMIT 1"
      )
      .get(bill.id) as { raw_text: string } | undefined;
    dbWrite.close();

    if (!version?.raw_text) {
      return NextResponse.json(
        { error: "Bill text not available from Congress.gov" },
        { status: 500 }
      );
    }

    // Step 3: Write text to temp file, run process pipeline
    const tmpDir = mkdtempSync(path.join(os.tmpdir(), "porkchop-"));
    const tmpFile = path.join(tmpDir, "bill.txt");
    writeFileSync(tmpFile, version.raw_text);

    try {
      await execAsync(
        `python3 -m porkchop.cli process "${tmpFile}" --bill-id ${sanitizedId}`,
        { env, cwd: PROJECT_ROOT, timeout: 120000 }
      );
    } finally {
      try {
        unlinkSync(tmpFile);
        rmdirSync(tmpDir);
      } catch {
        // cleanup failure is non-fatal
      }
    }

    // Step 4: Heuristic pork scoring (free, no AI)
    await execAsync(`python3 -m porkchop.cli score ${bill.id}`, {
      env,
      cwd: PROJECT_ROOT,
      timeout: 60000,
    });

    return NextResponse.json({
      status: "processed",
      billDbId: bill.id,
      title: bill.title,
      message: "Bill fetched, processed, and scored.",
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Processing failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
