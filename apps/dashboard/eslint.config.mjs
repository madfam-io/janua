// Flat config for @janua/dashboard. Replaces .eslintrc.json.
// All rule severities and both no-restricted-syntax selectors are carried over
// verbatim from the eslintrc file. The tailwindcss rules are quarantined — see
// the dated note below.

import { ignores, javascriptConfig, typescriptConfig, testOverrides } from '../../eslint.config.mjs';
import { nextCoreWebVitals } from '../../eslint.next.mjs';

// 2026-08-06 — the tailwindcss rules are temporarily NOT registered.
//
// This app is on tailwindcss 4.3.0, but eslint-plugin-tailwindcss is pinned to
// ^3.18.3, and v3 cannot read a v4 install: it aborts the whole ESLint run with
// "Error: Could not resolve tailwindcss" (tailwind-api-utils loadConfigV4), so
// registering it yields exit code 2 and ZERO findings for every other rule.
//
// This was invisible until now only because `next lint` has been dead since the
// pnpm override moved next to >=16.2.6 (Next 16 removed the `lint` subcommand),
// so this config had no live consumer.
//
// PR #432 (eslint-plugin-tailwindcss 3 -> 4) is the fix; re-register the plugin
// and the four tailwindcss/* rules below when it lands. Tracked in the
// follow-up issue linked from the migration PR.
//
// The whitelist and settings are preserved here verbatim so the restore is a
// pure re-registration, not a rewrite. Note `config` is tailwind.config.js —
// that is the file that actually exists in this app.
export const tailwindSettings = {
  callees: ['cn', 'clsx', 'cva'],
  config: 'tailwind.config.js',
  whitelist: [
  'bg-background',
  'bg-foreground',
  'bg-card',
  'bg-popover',
  'bg-primary',
  'bg-secondary',
  'bg-muted',
  'bg-accent',
  'bg-destructive',
  'bg-border',
  'bg-input',
  'bg-ring',
  'bg-brand',
  'bg-success',
  'bg-warning',
  'bg-info',
  'text-background',
  'text-foreground',
  'text-card',
  'text-card-foreground',
  'text-popover',
  'text-popover-foreground',
  'text-primary',
  'text-primary-foreground',
  'text-secondary',
  'text-secondary-foreground',
  'text-muted',
  'text-muted-foreground',
  'text-accent',
  'text-accent-foreground',
  'text-destructive',
  'text-destructive-foreground',
  'text-brand',
  'text-brand-foreground',
  'text-success',
  'text-success-foreground',
  'text-warning',
  'text-warning-foreground',
  'text-info',
  'text-info-foreground',
  'border-border',
  'border-input',
  'border-ring',
  'border-primary',
  'border-secondary',
  'border-destructive',
  'ring-ring',
  'ring-primary',
    'ring-destructive',
  ],
};

/** The four rules to restore alongside `tailwindSettings` once PR #432 lands. */
export const tailwindRules = {
  'tailwindcss/classnames-order': 'warn',
  'tailwindcss/enforces-negative-arbitrary-values': 'warn',
  'tailwindcss/enforces-shorthand': 'warn',
  'tailwindcss/no-contradicting-classname': 'error',
};

export default [
  ignores,
  javascriptConfig,
  typescriptConfig,
  nextCoreWebVitals,
  {
    files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
    rules: {
      'max-lines': ['warn', { max: 600, skipBlankLines: true, skipComments: true }],
      'max-lines-per-function': [
        'warn',
        { max: 200, skipBlankLines: true, skipComments: true },
      ],
      'no-restricted-syntax': [
        'warn',
        {
          selector: 'Literal[value=/^#[0-9a-fA-F]{3,8}$/]',
          message:
            'Hardcoded HEX colors are not allowed. Use CSS variables (e.g., bg-background, text-foreground) or semantic Tailwind classes instead.',
        },
        {
          selector:
            'Literal[value=/(bg|text|border)-(red|blue|green|yellow|gray|slate|zinc|neutral|stone|orange|amber|lime|emerald|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)-\\d{2,3}$/]',
          message:
            'Use semantic Tailwind colors (primary, secondary, destructive, muted) instead of raw color classes. Exception: opacity variants like bg-green-500/10 are allowed.',
        },
      ],
    },
  },
  {
    files: ['**/*.tsx', '**/*.ts'],
    rules: {
      'max-lines': ['error', { max: 800, skipBlankLines: true, skipComments: true }],
    },
  },
  {
    files: ['**/globals.css', '**/tailwind.config.ts', '**/tailwind.config.js'],
    rules: {
      'max-lines': 'off',
      'no-restricted-syntax': 'off',
    },
  },
  testOverrides,
];
