/** API response helpers (server-side) */

import { APP_VERSION } from "./config";
import { NextResponse } from "next/server";

export function apiResponse<T>(data: T) {
  return NextResponse.json({
    data,
    meta: {
      timestamp: new Date().toISOString(),
      version: APP_VERSION,
    },
  });
}

export function apiError(code: string, message: string, status = 400) {
  return NextResponse.json(
    { error: { code, message } },
    { status }
  );
}
