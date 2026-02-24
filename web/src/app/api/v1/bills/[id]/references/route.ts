import { getReferences } from "@/lib/db";
import { apiResponse } from "@/lib/api";
import type { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const refType = request.nextUrl.searchParams.get("type") || undefined;
  return apiResponse(getReferences(Number(id), refType));
}
