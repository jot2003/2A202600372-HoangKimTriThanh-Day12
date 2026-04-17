import { NextRequest, NextResponse } from "next/server";
import { streamAgent } from "@/lib/ai/agent";
import { checkApiKey, checkAndRecordBudget, checkRateLimit } from "@/lib/server/guards";

export type ChatRequestBody = {
  message: string;
  history?: { role: "user" | "model"; text: string }[];
  aiConfig?: { provider: "gemini" | "chatgpt"; apiKey?: string };
};

function normalizeText(input: string) {
  return input
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function detectRequiredCourseCodes(message: string): string[] {
  const msg = normalizeText(message);
  const matched = new Set<string>();
  const rules: Array<{ code: string; patterns: RegExp[] }> = [
    {
      code: "MI1124",
      patterns: [/giai\s*tich\s*(ii|2)\b/, /\bmi1124\b/i],
    },
    {
      code: "PH1120",
      patterns: [/vat\s*ly\s*(ii|2)\b/, /\bph1120\b/i],
    },
  ];
  for (const rule of rules) {
    if (rule.patterns.some((p) => p.test(msg))) {
      matched.add(rule.code);
    }
  }
  return [...matched];
}

function enrichMessageWithRequiredCourses(message: string) {
  const requiredCodes = detectRequiredCourseCodes(message);
  if (requiredCodes.length === 0) return message;
  return `${message}\n\n[RÀNG BUỘC HỆ THỐNG: Đây là các môn BẮT BUỘC trong kết quả và không được bỏ sót: ${requiredCodes.join(", ")}. Nếu có mã tương đương đang mở lớp thì vẫn phải đảm bảo đúng 2 môn tương ứng.]`;
}

export async function POST(req: NextRequest) {
  const startedAt = Date.now();
  try {
    const body = (await req.json()) as ChatRequestBody;
    const userId = req.headers.get("x-user-id") || "anonymous";
    const auth = checkApiKey(req.headers.get("x-api-key"));
    if (!auth.ok) {
      return NextResponse.json({ error: auth.message }, { status: 401 });
    }
    const rate = checkRateLimit(userId);
    if (!rate.ok) {
      return NextResponse.json(
        { error: "Rate limit exceeded" },
        { status: 429, headers: { "Retry-After": String(rate.retryAfter || 60) } }
      );
    }
    const budget = checkAndRecordBudget(userId, 0.05);
    if (!budget.ok) {
      return NextResponse.json({ error: "Monthly budget exceeded" }, { status: 402 });
    }
    const provider = body.aiConfig?.provider;
    const aiConfig =
      provider === "gemini" || provider === "chatgpt"
        ? { provider, apiKey: body.aiConfig?.apiKey?.trim() || undefined }
        : undefined;

    if (!body.message?.trim()) {
      return NextResponse.json({ error: "Message is required" }, { status: 400 });
    }

    const enrichedMessage = enrichMessageWithRequiredCourses(body.message);
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const event of streamAgent(enrichedMessage, body.history || [], aiConfig)) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
          }
        } catch (err) {
          const message = err instanceof Error ? err.message : "Agent error";
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "error", message })}\n\n`)
          );
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error(
      JSON.stringify({
        event: "chat_error",
        path: "/api/chat",
        error: error instanceof Error ? error.message : "Internal server error",
      })
    );
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  } finally {
    console.log(
      JSON.stringify({
        event: "chat_request",
        path: "/api/chat",
        duration_ms: Date.now() - startedAt,
      })
    );
  }
}
