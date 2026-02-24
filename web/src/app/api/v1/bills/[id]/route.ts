import { getBill } from "@/lib/db";
import { apiResponse, apiError } from "@/lib/api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const bill = getBill(Number(id));
  if (!bill) return apiError("NOT_FOUND", `Bill ${id} not found`, 404);
  return apiResponse(bill);
}
