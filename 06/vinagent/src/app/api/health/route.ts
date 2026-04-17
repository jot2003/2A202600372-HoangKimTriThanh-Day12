import { NextResponse } from "next/server";

const START = Date.now();

export async function GET() {
  return NextResponse.json({
    status: "ok",
    service: "vinagent-web",
    uptime_seconds: Math.floor((Date.now() - START) / 1000),
    timestamp: new Date().toISOString(),
  });
}
