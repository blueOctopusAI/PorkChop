import { NextRequest, NextResponse } from "next/server";

const PORKCHOP_API_URL =
  process.env.PORKCHOP_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const { billId, congressApiKey } = await req.json();

    if (!billId) {
      return NextResponse.json(
        { error: "billId is required (e.g., HR-10515)" },
        { status: 400 }
      );
    }

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

    // Call the PorkChop FastAPI server
    const response = await fetch(`${PORKCHOP_API_URL}/api/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bill_id: billId,
        congress_api_key: apiKey,
      }),
    });

    const data = await response.json();

    // The FastAPI returns either a ProcessResponse or ErrorResponse
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: 500 });
    }

    // Map snake_case response to camelCase for frontend compatibility
    return NextResponse.json({
      status: data.status,
      billDbId: data.bill_db_id,
      title: data.title,
      message: data.message,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Processing failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
