import { NextResponse } from "next/server";

export async function GET() {
  const hasApiKey = Boolean(process.env.AGENT_API_KEY);
  const hasProviderKey = Boolean(process.env.GOOGLE_API_KEY || process.env.OPENAI_API_KEY);

  if (!hasApiKey) {
    return NextResponse.json(
      { ready: false, reason: "AGENT_API_KEY is missing" },
      { status: 503 }
    );
  }

  return NextResponse.json({
    ready: true,
    ai_provider_key: hasProviderKey ? "configured" : "missing_optional",
    timestamp: new Date().toISOString(),
  });
}
