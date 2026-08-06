#!/usr/bin/env node
/**
 * Guards against tests that exist but can never run.
 *
 * The failure mode this exists to prevent is not "a test failed" -- it is a
 * workspace quietly accumulating test files that no command invokes, so CI is
 * green because it ran nothing. janua reached 129 TypeScript test files across
 * 16 workspaces while CI executed 4 of them.
 *
 * Two checks, both of which must fail loudly:
 *
 *   1. A workspace with test files must declare a `test` script.
 *      Workspaces listed in KNOWN_UNWIRED are recorded, pre-existing debt: they
 *      are reported every run but do not fail the build. Anything NOT on that
 *      list fails, so a new workspace cannot silently join the dead pile.
 *
 *   2. A workspace on ENFORCED must actually still contain test files. Without
 *      this, deleting or moving every test out of a wired workspace would make
 *      the guard pass by finding nothing -- exactly the green-by-vacuity shape
 *      the guard exists to catch.
 *
 * Run from the repo root: node scripts/check-test-scripts.mjs
 */

import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs'
import { join, relative, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..')

/**
 * Workspaces whose suites are wired into CI. Each MUST have test files and a
 * `test` script. Add to this list as dead suites are revived.
 */
const ENFORCED = [
  'packages/ui',
  'packages/core',
  'packages/cli',
  'apps/dashboard',
  'apps/website',
  'apps/admin',
]

/**
 * Known-dead suites: test files exist but nothing runs them. This is recorded
 * technical debt, NOT an exemption to grow. Reviving a workspace means moving
 * it from here to ENFORCED. Adding a new entry here should be a conscious
 * decision made in review, not a reflex to silence the guard.
 */
const KNOWN_UNWIRED = [
  'packages/typescript-sdk',
  'packages/react-sdk',
  'packages/mock-api',
  'packages/vue-sdk',
  'packages/jwt-utils',
  'packages/nextjs-sdk',
  'packages/monitoring',
  'packages/edge',
  'apps/docs',
  'apps/edge-verify',
]

/** apps/api is Python (pytest, wired separately via `pnpm test:api`). */
const IGNORED_WORKSPACES = ['apps/api']

const TEST_FILE_RE = /\.(test|spec)\.(ts|tsx|js|jsx|mjs|cjs)$/
const SKIP_DIRS = new Set(['node_modules', '.next', 'dist', 'build', 'coverage', '.turbo'])

/** Playwright lives in these; they are run by the e2e workflow, not unit CI. */
const E2E_DIR_RE = /(^|\/)(tests-e2e|e2e)(\/|$)/

function countTestFiles(dir, base = dir) {
  let count = 0
  let entries
  try {
    entries = readdirSync(dir, { withFileTypes: true })
  } catch {
    return 0
  }
  for (const entry of entries) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue
      if (E2E_DIR_RE.test(relative(base, full).split('\\').join('/'))) continue
      count += countTestFiles(full, base)
    } else if (TEST_FILE_RE.test(entry.name)) {
      count += 1
    }
  }
  return count
}

function discoverWorkspaces() {
  const found = []
  for (const group of ['packages', 'apps']) {
    const groupDir = join(repoRoot, group)
    if (!existsSync(groupDir)) continue
    for (const name of readdirSync(groupDir)) {
      const dir = join(groupDir, name)
      if (!statSync(dir).isDirectory()) continue
      if (!existsSync(join(dir, 'package.json'))) continue
      found.push({ id: `${group}/${name}`, dir })
    }
  }
  return found.sort((a, b) => a.id.localeCompare(b.id))
}

const errors = []
const warnings = []
const ok = []

const workspaces = discoverWorkspaces()
const seen = new Set(workspaces.map((w) => w.id))

for (const { id, dir } of workspaces) {
  if (IGNORED_WORKSPACES.includes(id)) continue

  const testFiles = countTestFiles(dir)
  let pkg
  try {
    pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'))
  } catch (err) {
    errors.push(`${id}: package.json is unreadable (${err.message})`)
    continue
  }
  const testScript = pkg.scripts?.test

  if (ENFORCED.includes(id)) {
    // Anti-blinding: a wired workspace that has lost its tests is a failure.
    if (testFiles === 0) {
      errors.push(
        `${id}: listed as ENFORCED but contains ZERO test files. Either the ` +
          `tests moved (point the guard at their new home) or they were ` +
          `deleted. A wired workspace with nothing to run is the exact ` +
          `green-by-vacuity this guard exists to catch.`
      )
      continue
    }
    if (!testScript) {
      errors.push(`${id}: has ${testFiles} test file(s) but no "test" script.`)
      continue
    }
    // `vitest`/`jest --watch` never exit; in CI they hang until timeout.
    if (/\bvitest\b(?!.*\brun\b)/.test(testScript) || /--watch\b/.test(testScript)) {
      errors.push(
        `${id}: "test" script (${testScript}) runs in watch mode and will ` +
          `never exit in CI. Use "vitest run" / drop --watch.`
      )
      continue
    }
    ok.push(`${id}: ${testFiles} test file(s), test = "${testScript}"`)
    continue
  }

  if (testFiles > 0 && !testScript) {
    if (KNOWN_UNWIRED.includes(id)) {
      warnings.push(`${id}: ${testFiles} test file(s), no "test" script (known debt)`)
    } else {
      errors.push(
        `${id}: has ${testFiles} test file(s) but no "test" script, and is not ` +
          `on KNOWN_UNWIRED. Wire it up, or record it deliberately in ` +
          `scripts/check-test-scripts.mjs.`
      )
    }
  } else if (testFiles > 0 && testScript && !KNOWN_UNWIRED.includes(id)) {
    warnings.push(
      `${id}: ${testFiles} test file(s) and a "test" script, but is not in ` +
        `ENFORCED -- nothing in CI invokes it.`
    )
  } else if (testFiles > 0) {
    warnings.push(`${id}: ${testFiles} test file(s), not run by CI (known debt)`)
  }
}

// Stale-list check: a list entry naming a workspace that no longer exists means
// the guard is silently covering nothing.
for (const id of [...ENFORCED, ...KNOWN_UNWIRED]) {
  if (!seen.has(id)) {
    errors.push(`${id}: named in the guard's lists but no such workspace exists.`)
  }
}

if (ok.length) {
  console.log('Wired and enforced:')
  for (const line of ok) console.log(`  ok  ${line}`)
}
if (warnings.length) {
  console.log('\nNot run by CI (recorded debt):')
  for (const line of warnings) console.log(`  --  ${line}`)
}
if (errors.length) {
  console.error('\nFAIL: test suites that cannot run\n')
  for (const line of errors) console.error(`  !!  ${line}`)
  console.error(
    `\n${errors.length} problem(s). A test file that no command runs is not ` +
      `coverage.\n`
  )
  process.exit(1)
}

console.log(`\n${ok.length} workspace(s) enforced, ${warnings.length} recorded as debt.`)
