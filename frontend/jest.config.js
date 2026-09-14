const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const customJestConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  // e2e/ holds the Playwright suite (Step 4) — a separate runner (`npm run
  // test:e2e`), not Jest; its specs import @playwright/test, incompatible
  // with Jest's runner.
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/.next/", "<rootDir>/e2e/"],
};

module.exports = createJestConfig(customJestConfig);
