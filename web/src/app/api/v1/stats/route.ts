import { getStats } from "@/lib/db";
import { apiResponse } from "@/lib/api";

export async function GET() {
  return apiResponse(getStats());
}
