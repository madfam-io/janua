/**
 * Barrel-export integrity for @janua/ui.
 *
 * Every symbol packages/ui/src/index.ts claims to re-export from
 * './components/auth' must actually be reachable through that barrel.
 *
 * Why this exists: on 2026-08-02 the password-policy helpers were re-exported
 * from './components/auth' while living in './lib/password-policy'. That
 * type-checks in isolation, so CI's typecheck stayed green — but Turbopack
 * resolves the barrel at bundle time, finds nothing, and fails the build. It
 * broke EVERY frontend image (website, admin, dashboard) for two days, which
 * is why the session-cookie bridge fix (#476) never reached production and
 * app.janua.dev hung after login. Typecheck cannot see this class; this can.
 *
 * usage: node scripts/check-ui-barrel-exports.mjs
 */
import { readFileSync, existsSync, statSync } from 'node:fs';
import { resolve, dirname } from 'node:path';

const ROOT = resolve(import.meta.dirname, '../packages/ui/src');
const idx = readFileSync(resolve(ROOT, 'index.ts'), 'utf8');

// No braces inside an export list, so [^}]* anchors to the right block —
// [\s\S]*? starts at the FIRST `export {` in the file and swallows everything.
const block = idx.match(/export \{([^}]*)\} from '\.\/components\/auth'/);
if (!block) {
  console.error('could not find the ./components/auth export block');
  process.exit(1);
}
const claimed = block[1]
  .split('\n')
  .map((l) => l.replace(/\/\/.*/, '').trim().replace(/,$/, ''))
  .filter(Boolean)
  .map((s) => s.replace(/^type\s+/, ''));

/** Collect exported names reachable from a barrel, following `export *`. */
function reachable(file, seen = new Set()) {
  const abs = ['.ts', '.tsx', '/index.ts', '/index.tsx', '']
    .map((ext) => file + ext)
    .find((p) => existsSync(p) && statSync(p).isFile());
  if (!abs || seen.has(abs)) return new Set();
  seen.add(abs);
  const src = readFileSync(abs, 'utf8');
  const names = new Set();

  for (const m of src.matchAll(/export\s+(?:const|function|class|interface|type|enum)\s+(\w+)/g)) {
    names.add(m[1]);
  }
  for (const m of src.matchAll(/export\s*\{([^}]*)\}(?!\s*from)/g)) {
    for (const n of m[1].split(',')) {
      const c = n.replace(/\/\/.*/, '').trim().replace(/^type\s+/, '').split(/\s+as\s+/).pop();
      if (c) names.add(c.trim());
    }
  }
  for (const m of src.matchAll(/export\s*\{([^}]*)\}\s*from\s*'([^']+)'/g)) {
    for (const n of m[1].split(',')) {
      const c = n.replace(/\/\/.*/, '').trim().replace(/^type\s+/, '').split(/\s+as\s+/).pop();
      if (c) names.add(c.trim());
    }
  }
  for (const m of src.matchAll(/export\s*\*\s*from\s*'([^']+)'/g)) {
    for (const n of reachable(resolve(dirname(abs), m[1]), seen)) names.add(n);
  }
  return names;
}

const available = reachable(resolve(ROOT, 'components/auth'));
const missing = claimed.filter((c) => !available.has(c));

console.log(`claimed from './components/auth': ${claimed.length}`);
console.log(`reachable through that barrel:    ${available.size}`);
if (missing.length) {
  console.error(`\n✗ NOT REACHABLE (would fail the bundler):`);
  for (const m of missing) console.error(`   - ${m}`);
  process.exit(1);
}
console.log('\n✓ every claimed symbol resolves through the auth barrel');

// And the moved symbols must now be reachable from their real home.
const lib = reachable(resolve(ROOT, 'lib/password-policy'));
for (const n of ['PASSWORD_SPECIAL_CHARS', 'validatePasswordPolicy']) {
  console.log(`${lib.has(n) ? '✓' : '✗'} ${n} exported from lib/password-policy`);
  if (!lib.has(n)) process.exitCode = 1;
}
console.log(
  /export \* from '\.\/lib\/password-policy'/.test(idx)
    ? '✓ index.ts re-exports lib/password-policy'
    : '✗ index.ts does NOT re-export lib/password-policy',
);
