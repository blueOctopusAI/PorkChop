import { getSections } from "@/lib/db";
import { apiResponse } from "@/lib/api";
import type { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const versionId =
    Number(request.nextUrl.searchParams.get("version_id")) || undefined;
  return apiResponse(getSections(Number(id), versionId));
}
