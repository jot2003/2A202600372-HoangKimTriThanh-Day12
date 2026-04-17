const fs = require("fs");
const path = require("path");

const base = __dirname;
const checks = [
  "Dockerfile",
  "docker-compose.yml",
  ".dockerignore",
  ".env.example",
  "railway.toml",
  "render.yaml",
  "src/app/api/health/route.ts",
  "src/app/api/ready/route.ts",
  "src/app/api/chat/route.ts",
  "src/lib/server/guards.ts",
];

let passed = 0;
console.log("== VinAgent Lab12 Packaging Check ==");
for (const rel of checks) {
  const ok = fs.existsSync(path.join(base, rel));
  if (ok) passed += 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${rel}`);
}
console.log(`Result: ${passed}/${checks.length}`);
process.exit(passed === checks.length ? 0 : 1);
