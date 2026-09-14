import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const BACKEND_DIR = path.resolve(__dirname, "../../backend");
const BACKEND_PYTHON = process.env.E2E_BACKEND_PYTHON || path.join(BACKEND_DIR, ".venv/bin/python");
const MAILPIT_URL = process.env.E2E_MAILPIT_URL || "http://localhost:8025";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "E2eDevOnly!2026";

export const FIXTURES_PATH = path.resolve(__dirname, ".fixtures.json");

async function globalSetup() {
  if (!fs.existsSync(BACKEND_PYTHON)) {
    throw new Error(
      `Backend Python not found at ${BACKEND_PYTHON}. Set E2E_BACKEND_PYTHON, or create backend/.venv ` +
        `per docs/DATABASE.md before running the E2E suite.`
    );
  }

  // Clear Mailpit so email-lookup helpers only ever see mail from this run.
  await fetch(`${MAILPIT_URL}/api/v1/messages`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ IDs: [] }),
  }).catch((err) => {
    throw new Error(`Could not reach Mailpit at ${MAILPIT_URL} — is docker compose up? (${err.message})`);
  });

  const output = execFileSync(
    BACKEND_PYTHON,
    ["manage.py", "seed_e2e", `--admin-password=${ADMIN_PASSWORD}`],
    { cwd: BACKEND_DIR, encoding: "utf-8" }
  );
  const fixtures = JSON.parse(output.trim());
  fixtures.adminPassword = ADMIN_PASSWORD;
  fixtures.mailpitUrl = MAILPIT_URL;

  fs.writeFileSync(FIXTURES_PATH, JSON.stringify(fixtures, null, 2));
}

export default globalSetup;
