#!/usr/bin/env node
/**
 * Repo-wide lint runner with a ratchet.
 *
 * Background (2026-08-06)
 * -----------------------
 * `pnpm lint` used to be `cd packages/core && npm run lint` — one workspace out
 * of eighteen, reporting green for the whole repo. Migrating off eslintrc to
 * flat config made it possible to point ESLint at every workspace, which
 * immediately surfaced a large backlog of pre-existing findings.
 *
 * Rather than suppress that backlog with a blanket `|| true`, this runner
 * splits the workspaces in two:
 *
 *   BLOCKING  — currently at zero errors. Regressions here fail the build, so
 *               these workspaces can never slide back.
 *   REPORTING — carries pre-existing errors. Counts are printed in full and the
 *               build is NOT failed, so the migration can land without either
 *               hiding the debt or holding every other PR hostage to it.
 *
 * The ratchet: as a workspace's errors reach zero, move it into BLOCKING. The
 * goal is an empty REPORTING list. Tracked in the follow-up issue linked from
 * the flat-config migration PR.
 *
 * No rule is disabled and no finding is suppressed to achieve this — every
 * error below is real and still reported on every run.
 */

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** Zero errors as of 2026-08-06. Any error here fails the build. */
const BLOCKING = ['packages/core', 'apps/docs', 'apps/website', 'apps/admin'];

/**
 * Pre-existing errors as of 2026-08-06 (counts measured at migration time).
 * Reported, not enforced. Move each entry to BLOCKING once it reaches zero.
 */
const REPORTING = [
  'packages/typescript-sdk', // 24 errors: no-unused-vars, no-useless-escape, no-useless-catch
  'packages/feature-flags', //  4 errors: no-case-declarations
  'packages/react-native-sdk', //  3 errors: no-unused-vars
  'apps/dashboard', //  7 errors: max-lines, react/display-name, no-unescaped-entities, no-html-link-for-pages
];

function lint(ws) {
  const cwd = join(repoRoot, ws);
  if (!existsSync(join(cwd, 'package.json'))) return null;
  const pkg = JSON.parse(readFileSync(join(cwd, 'package.json'), 'utf8'));
  if (!pkg.scripts?.lint) return null;

  let out = '';
  try {
    out = execFileSync('npx', ['eslint', '.', '-f', 'json'], {
      cwd,
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err) {
    out = err.stdout ?? '';
    if (!out.trim()) {
      // Exit code 2 = ESLint could not run at all (bad config, missing plugin).
      // That is always a hard failure, whichever list the workspace is in.
      console.error(`\n${ws}: ESLint failed to run\n${err.stderr ?? err.message}`);
      return { errors: -1, warnings: 0, files: 0, fatal: true };
    }
  }

  let results;
  try {
    results = JSON.parse(out);
  } catch {
    console.error(`\n${ws}: could not parse ESLint JSON output`);
    return { errors: -1, warnings: 0, files: 0, fatal: true };
  }

  let errors = 0;
  let warnings = 0;
  const rules = new Map();
  for (const f of results) {
    errors += f.errorCount;
    warnings += f.warningCount;
    for (const m of f.messages) {
      const key = `${m.severity === 2 ? 'error' : 'warn'}  ${m.ruleId ?? '(parse)'}`;
      rules.set(key, (rules.get(key) ?? 0) + 1);
    }
  }
  return { errors, warnings, files: results.length, rules };
}

let failed = false;
const rows = [];

for (const [list, isBlocking] of [
  [BLOCKING, true],
  [REPORTING, false],
]) {
  for (const ws of list) {
    const r = lint(ws);
    if (!r) continue;
    rows.push({ ws, ...r, isBlocking });

    if (r.fatal || (isBlocking && r.errors > 0)) failed = true;

    const tag = isBlocking ? 'BLOCKING ' : 'reporting';
    console.log(
      `${tag}  ${ws.padEnd(28)} errors=${String(r.errors).padStart(3)}  warnings=${String(
        r.warnings
      ).padStart(4)}  files=${r.files}`
    );
    if (r.rules) {
      for (const [rule, n] of [...r.rules].sort((a, b) => b[1] - a[1]).slice(0, 6)) {
        console.log(`             ${String(n).padStart(4)}  ${rule}`);
      }
    }
  }
}

const totals = rows.reduce(
  (a, r) => ({ errors: a.errors + Math.max(r.errors, 0), warnings: a.warnings + r.warnings }),
  { errors: 0, warnings: 0 }
);
console.log(`\nTOTAL  errors=${totals.errors}  warnings=${totals.warnings}`);

if (failed) {
  console.error('\nFAIL: a blocking workspace reported errors, or ESLint could not run.');
  process.exit(1);
}
if (totals.errors > 0) {
  console.log(
    '\nPASS (blocking set clean). Errors remain in the reporting set — see scripts/lint-workspaces.mjs.'
  );
}
