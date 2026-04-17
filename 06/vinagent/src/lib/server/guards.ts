type RateEntry = { ts: number };
type SpendEntry = { total: number; month: string };

const memoryRateStore = new Map<string, RateEntry[]>();
const memorySpendStore = new Map<string, SpendEntry>();

function getMonthKey(): string {
  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function checkApiKey(providedKey: string | null): { ok: boolean; message?: string } {
  const expected = process.env.AGENT_API_KEY;
  if (!expected) {
    return { ok: false, message: "AGENT_API_KEY is not configured" };
  }
  if (!providedKey || providedKey !== expected) {
    return { ok: false, message: "Invalid or missing API key" };
  }
  return { ok: true };
}

export function checkRateLimit(userId: string): { ok: boolean; retryAfter?: number } {
  const windowMs = 60_000;
  const limit = Number(process.env.RATE_LIMIT_PER_MINUTE || "10");
  const now = Date.now();

  const entries = memoryRateStore.get(userId) || [];
  const recent = entries.filter((entry) => now - entry.ts <= windowMs);
  if (recent.length >= limit) {
    return { ok: false, retryAfter: 60 };
  }
  recent.push({ ts: now });
  memoryRateStore.set(userId, recent);
  return { ok: true };
}

export function checkAndRecordBudget(userId: string, estimatedCost = 0.05): { ok: boolean } {
  const monthlyBudget = Number(process.env.MONTHLY_BUDGET_USD || "10");
  const monthKey = getMonthKey();
  const key = `${userId}:${monthKey}`;
  const current = memorySpendStore.get(key) || { total: 0, month: monthKey };
  if (current.total + estimatedCost > monthlyBudget) {
    return { ok: false };
  }
  memorySpendStore.set(key, { total: current.total + estimatedCost, month: monthKey });
  return { ok: true };
}
