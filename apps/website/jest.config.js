// The previous config declared `preset: 'ts-jest'`, but ts-jest is not a
// dependency of this app and pnpm's strict node_modules meant it could never
// resolve -- so jest failed before collecting a single test.
//
// Runner choice: these tests use only globals (describe/it/expect), so they run
// under jest like the sibling Next.js apps. packages/ui is on vitest because
// its files import from 'vitest'.
const createNextAppJestConfig = require('../../jest.next-app')

module.exports = createNextAppJestConfig({
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    // The Playwright specs live in tests-e2e/, NOT tests/e2e/ as the previous
    // config assumed -- so jest's default testMatch would have collected them
    // and failed on the `@playwright/test` imports.
    '<rootDir>/tests-e2e/',
  ],
})
