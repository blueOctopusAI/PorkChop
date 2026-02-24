import { getVersions } from "@/lib/db";
import { apiResponse } from "@/lib/api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return apiResponse(getVersions(Number(id)));
}
