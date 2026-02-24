import { searchBills } from "@/lib/db";
import { apiResponse, apiError } from "@/lib/api";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q");
  if (!query) {
    return apiError("BAD_REQUEST", "Query parameter 'q' required");
  }
  return apiResponse(searchBills(query));
}
