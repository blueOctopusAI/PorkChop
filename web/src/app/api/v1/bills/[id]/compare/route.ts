import { getComparison } from "@/lib/db";
import { apiResponse, apiError } from "@/lib/api";
import type { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const fromId = Number(request.nextUrl.searchParams.get("from"));
  const toId = Number(request.nextUrl.searchParams.get("to"));
  if (!fromId || !toId) {
    return apiError("BAD_REQUEST", "Both 'from' and 'to' version IDs required");
  }
  const comparison = getComparison(Number(id), fromId, toId);
  if (!comparison) {
    return apiError("NOT_FOUND", "Comparison not found", 404);
  }
  return apiResponse(comparison);
}
