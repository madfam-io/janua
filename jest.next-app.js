// Shared jest config factory for the Next.js apps (dashboard, website, admin).
//
// Uses next/jest so each app gets its own SWC transform, next.config and CSS
// module handling. Two things next/jest does NOT solve on its own, and which
// previously stopped every one of these suites from loading:
//
//  1. `@/*` — the apps declare `paths` in tsconfig but no `baseUrl`, so
//     next/jest does not derive a moduleNameMapper from them.
//
//  2. `@janua/*` — the workspace SDKs resolve through package.json "exports"
//     to `dist/`, which is a build artifact that does not exist on a clean
//     checkout. Unit tests must not depend on a prior build step, so the
//     dist-published packages are mapped to their TypeScript sources. The src
//     tree mirrors the dist tree (src/app/client.ts <-> dist/app/client.js),
//     so subpath imports map across unchanged.
//
// @janua/ui is deliberately absent: its package.json already points at
// ./src/index.ts, so it resolves to source without help.
const nextJest = require('next/jest')

const workspaceSourceMappings = {
  // Longest-prefix first: subpath patterns must precede their bare package.
  '^@janua/typescript-sdk/(.*)$': '<rootDir>/../../packages/typescript-sdk/src/$1',
  '^@janua/typescript-sdk$': '<rootDir>/../../packages/typescript-sdk/src/index.ts',
  '^@janua/nextjs/(.*)$': '<rootDir>/../../packages/nextjs-sdk/src/$1',
  '^@janua/nextjs$': '<rootDir>/../../packages/nextjs-sdk/src/index.ts',
  '^@janua/react-sdk/(.*)$': '<rootDir>/../../packages/react-sdk/src/$1',
  '^@janua/react-sdk$': '<rootDir>/../../packages/react-sdk/src/index.ts',
  '^@janua/feature-flags/(.*)$': '<rootDir>/../../packages/feature-flags/src/$1',
  '^@janua/feature-flags$': '<rootDir>/../../packages/feature-flags/src/index.ts',
}

/**
 * @param {import('jest').Config} overrides
 * @returns {() => Promise<import('jest').Config>}
 */
module.exports = function createNextAppJestConfig(overrides = {}) {
  const createJestConfig = nextJest({ dir: './' })

  const { moduleNameMapper: extraMappings, ...rest } = overrides

  return createJestConfig({
    testEnvironment: 'jest-environment-jsdom',
    moduleNameMapper: {
      ...workspaceSourceMappings,
      ...extraMappings,
      // Must stay last: '^@/(.*)$' would otherwise shadow nothing, but keeping
      // the broad alias after the specific ones documents the intended order.
      '^@/(.*)$': '<rootDir>/$1',
    },
    testPathIgnorePatterns: [
      '<rootDir>/node_modules/',
      '<rootDir>/.next/',
    ],
    ...rest,
  })
}
