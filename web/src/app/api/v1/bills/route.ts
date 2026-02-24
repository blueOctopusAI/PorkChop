import { listBills } from "@/lib/db";
import { apiResponse } from "@/lib/api";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const limit = Number(request.nextUrl.searchParams.get("limit")) || 50;
  const bills = listBills(limit);
  return apiResponse(bills);
}
