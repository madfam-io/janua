# pnpm Audit Triage — 2026-07-11

Triage of the automated daily pnpm-audit report
([issue #348](https://github.com/madfam-org/janua/issues/348), open since
2026-04-28).

- **Before:** `pnpm audit` reported **50 findings (9 low / 23 moderate / 18
  high)** across **38 unique advisories** in 15 packages.
- **After:** `pnpm audit` reports **No known vulnerabilities found**.
- **Mechanism:** every fix is a patch/minor bump **within the installed
  major**, applied through the existing `pnpm.overrides` block in the root
  `package.json` (the repo's established pattern) plus
  `pnpm install --no-frozen-lockfile` re-resolution. No source code changed.
- **Held major bumps:** none were required by this audit. The standing
  Dependabot holds (below) are unaffected and remain held.

## Fixed advisories

| Package | Advisories (GHSA) | Highest severity | Installed → resolved | Override | Notes |
| --- | --- | --- | --- | --- | --- |
| axios | hfxv-24rg-xrqf, 777c-7fjr-54vf, p92q-9vqr-4j8v, j5f8-grm9-p9fc, 35jp-ww65-95wh, pjwm-pj3p-43mv, 898c-q2cr-xwhg, 654m-c8p4-x5fp | high (6) | 1.15.2 → 1.18.0 | `axios: ">=1.16.0"` | Minor-range bump; 1.18.0 was already in the tree for other importers. |
| undici | vmh5-mc38-953g, 38rv-x7px-6hhq, vxpw-j846-p89q, p88m-4jfj-68fv, pr7r-676h-xcf6, 35p6-xmwp-9g52, g8m3-5g58-fq7m | high (3) | 8.3.0 → 8.7.0 | `undici: ">=8.5.0"` (was `>=6.19.8`) | Only 8.x existed in the lockfile, so raising the floor forces no cross-major jump. Reaches us via wrangler/miniflare (dev tooling in `apps/edge-verify`). |
| dompurify | cmwh-pvxp-8882, 76mc-f452-cxcm, hpcv-96wg-7vj8, r47g-fvhr-h676, rp9w-3fw7-7cwq, vxr8-fq34-vvx9, gvmj-g25r-r7wr, x4vx-rjvf-j5p4 | moderate (5) | 3.4.3 → 3.4.11 | `dompurify: ">=3.4.11"` (new) | Patch bumps. GHSA-x4vx-rjvf-j5p4 lists no patched version but its vulnerable range is `<=3.4.6`, so 3.4.11 is outside it. Via posthog-js in `apps/dashboard`. |
| vite | fx2h-pf6j-xcff, v6wh-96g9-6wx3 | high | 8.0.5 / 8.0.14 → 8.0.16 | `vite: "8.0.16"` (was exact-pin `8.0.5`) | Kept the exact-pin style introduced by the earlier security-audit fix (f50de5b6), moved forward to the patched release. |
| protobufjs | wcpc-wj8m-hjx6, f38q-mgvj-vph7 | high | 7.5.8 → 7.6.5 | `protobufjs: ">=7.6.3 <8.0.0"` (new) | Upper bound added deliberately — an unbounded override resolved to 8.x (major). Constrained to stay in 7.x. |
| js-yaml | h67p-54hq-rp68 (two fix lines) | moderate | 3.14.2 → 3.15.0 and 4.1.1 → 4.3.0 | `js-yaml@<4.0.0: ">=3.15.0 <4.0.0"`, `js-yaml@>=4.0.0: ">=4.2.0 <5.0.0"` (new) | Per-major targeted overrides so v3 consumers (legacy `safeLoad` API) are not forced onto v4+, and v4 consumers are not forced onto v5. |
| form-data | hmw2-7cc7-3qxx | high | 4.0.5 → 4.0.6 | `form-data: ">=4.0.6"` (new) | Patch bump. |
| ws | 96hv-2xvq-fx4p | high | 8.20.1 → 8.21.0 | `ws: ">=8.21.0"` (was `>=8.20.1`) | Minor bump. |
| linkify-it | 22p9-wv53-3rq4 | high | 5.0.0 → 5.0.2 | `linkify-it: ">=5.0.1"` (new) | Patch bump; markdown-it dependency in `packages/typescript-sdk`. |
| qs | q8mj-m7cp-5q26 | moderate | 6.15.0 / 6.15.1 → 6.15.3 | `qs: ">=6.15.2"` (was `>=6.14.2`) | Patch bump. |
| markdown-it | 6v5v-wf23-fmfq | moderate | 14.1.1 → 14.3.0 | `markdown-it: ">=14.2.0"` (was `>=14.1.1`) | Minor bump. |
| @opentelemetry/core | 8988-4f7v-96qf | moderate | 2.2.0 / 2.6.1 / 2.7.1 → 2.9.0 | `@opentelemetry/core: ">=2.8.0"` (new) | Within major 2; deduplicates three older copies. |
| @sveltejs/kit | hgv7-v322-mmgr | moderate | 2.59.1 → not installed | `@sveltejs/kit: ">=2.60.1"` (was `>=2.57.1`) | Was only an **optional peer** of `@vercel/analytics` in `apps/website`; after re-resolution the vulnerable copy is no longer installed at all. |
| esbuild | g7r4-m6w7-qqqr | low | 0.27.3 / 0.28.0 → 0.28.1 | `esbuild: ">=0.28.1"` (was `>=0.25.0"`) | 0.x minor is technically semver-major territory, but esbuild is build-time-only here and the repo already floats it via override; all package builds verified green (see Validation). |
| @babel/core | 4x5r-pxfx-6jf8 | low | 7.29.0 → 7.29.7 | `@babel/core: ">=7.29.6"` (new) | Patch bump. |

## Held (not bumped)

No advisory in this audit required a major-version bump, so nothing was held
*for the audit*. The standing holds from
[DEPENDABOT_SWEEP_2026-04-18.md](../../DEPENDABOT_SWEEP_2026-04-18.md) are
**not** pnpm-audit findings and remain held:

| Package | Held bump | Why held | Revisit condition |
| --- | --- | --- | --- |
| @simplewebauthn/server | 9.0.3 → 13.x | **Latent passkeys runtime break**: v13 moved `registrationInfo.{credentialID,credentialPublicKey,counter}` under `.credential.{id,publicKey,counter}`; `packages/core/src/services/webauthn.service.ts` still uses the v9 shape and unit tests mock the module, so green tests do not prove the bump. No open advisory against v9. | Rewrite webauthn.service registration/authentication verify paths for the v13 shape, add `@simplewebauthn/types`, remove the `src/services/**/*` tsconfig exclude (or add a typed integration test), then bump. |
| @react-native-async-storage/async-storage | 1.x → 3.x | RN New Architecture migration; needs device smoke test. | Coordinated RN SDK migration. |
| inquirer | 9.x → 13.x | CLI uses the legacy monolithic `inquirer.prompt` API; v10+ is modular/ESM-first. | Refactor `packages/cli/src/utils/prompts.ts` to `@inquirer/*`. |
| prisma / @prisma/client | 6.1.0 → 7.x | Major engine bump; needs schema compatibility review. | Dedicated coordinated upgrade. |

Python advisories are tracked separately in
[dependency-security-exceptions.md](dependency-security-exceptions.md)
(pip-audit gate); they are out of scope for the pnpm audit issue.

## Validation

`pnpm audit` after the bumps: **No known vulnerabilities found**.

Suites run in this worktree after re-resolution (all packages whose dependency
trees changed):

| Workspace | Result |
| --- | --- |
| packages/core | typecheck ✅, build ✅, jest 36/36 ✅ (includes webauthn tests) |
| packages/typescript-sdk | build (rollup + dts) ✅, jest 903/903 ✅ |
| packages/cli | vitest 7/7 ✅, build ✅ |
| packages/edge | vitest 7/7 ✅, tsup build ✅ |
| packages/react-sdk | jest 123/123 ✅, build ✅ |
| packages/vue-sdk | vitest 29/29 ✅, build ✅ |
| packages/nextjs-sdk | vitest 22/22 ✅, build ✅ |
| packages/ui | vitest 503 passed / 20 skipped ✅ (skips pre-existing) |
| apps/dashboard | typecheck ✅, `next build` ✅ |
| apps/website | `next build` ✅; jest 3 failures + 2 playwright-under-jest suite errors — **identical on origin/main baseline** (pre-existing) |
| apps/admin | typecheck/build fail on missing `@janua/feature-flags` + jest-dom types — **identical on origin/main baseline** (pre-existing) |
| apps/docs | typecheck/build fail on `@testing-library/react` types + tailwind-v4 PostCSS config — **identical on origin/main baseline** (pre-existing) |
| apps/edge-verify | no test/build scripts defined; undici change is dev-tooling (wrangler/miniflare) |

Pre-existing failures were confirmed by running the same commands in a clean
worktree at `origin/main` (55af5f53) with a frozen-lockfile install: failure
sets and signatures match exactly, so none of them are caused by these bumps.

## Revisit conditions

- Issue #348 self-updates daily; it should stop reporting once CI picks up
  this lockfile. Do not close it manually.
- If a future advisory requires crossing a major (e.g. protobufjs 8.x,
  js-yaml 5.x), remove the corresponding upper bound in `pnpm.overrides`
  **only** together with a consumer compatibility check.
- The `vite` exact pin (`8.0.16`) should be moved forward, not widened, on the
  next vite advisory (matches the original pin's intent).
