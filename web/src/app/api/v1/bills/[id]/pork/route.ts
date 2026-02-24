import { getPorkScores, getPorkSummary } from "@/lib/db";
import { apiResponse } from "@/lib/api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const billId = Number(id);
  return apiResponse({
    scores: getPorkScores(billId),
    summary: getPorkSummary(billId),
  });
}
