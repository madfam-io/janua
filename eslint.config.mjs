// Flat ESLint config for the Janua monorepo.
//
// Replaces the former .eslintrc.json. Flat config is the only format ESLint 10
// understands: ESLint 8 depended on @eslint/eslintrc ^2, ESLint 9 on ^3, and
// ESLint 10 dropped the eslintrc compatibility layer entirely.
//
// Each workspace has its own eslint.config.mjs that imports the pieces it needs
// from this file, so shared rules stay defined in exactly one place.

import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

/** Build artefacts and vendored code no workspace should ever lint. */
export const ignores = {
  ignores: [
    '**/dist/**',
    '**/build/**',
    '**/.next/**',
    '**/node_modules/**',
    '**/coverage/**',
    '**/storybook-static/**',
    '**/*.config.js',
    '**/*.config.mjs',
    '**/*.config.cjs',
    '**/*.config.ts',
    // ESLint has no CSS parser here; app/globals.css otherwise fails with
    // "Parsing error: Unexpected character '@'" (at the @tailwind directives).
    // The old eslintrc listed globals.css in an `overrides` block, but that
    // never ran because `next lint` was already broken.
    '**/*.css',
  ],
};

/** Globals formerly supplied by `env: { browser, node, es2021 }`. */
export const commonGlobals = {
  // node
  process: 'readonly',
  Buffer: 'readonly',
  __dirname: 'readonly',
  __filename: 'readonly',
  global: 'readonly',
  module: 'writable',
  require: 'readonly',
  exports: 'writable',
  console: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  setImmediate: 'readonly',
  clearImmediate: 'readonly',
  URL: 'readonly',
  URLSearchParams: 'readonly',
  TextEncoder: 'readonly',
  TextDecoder: 'readonly',
  AbortController: 'readonly',
  AbortSignal: 'readonly',
  // browser
  window: 'readonly',
  document: 'readonly',
  navigator: 'readonly',
  location: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  fetch: 'readonly',
  Request: 'readonly',
  Response: 'readonly',
  Headers: 'readonly',
  FormData: 'readonly',
  Blob: 'readonly',
  File: 'readonly',
  Event: 'readonly',
  CustomEvent: 'readonly',
  EventTarget: 'readonly',
  MessageChannel: 'readonly',
  MessageEvent: 'readonly',
  WebSocket: 'readonly',
  crypto: 'readonly',
  performance: 'readonly',
  queueMicrotask: 'readonly',
  structuredClone: 'readonly',
  requestAnimationFrame: 'readonly',
  cancelAnimationFrame: 'readonly',
  HTMLElement: 'readonly',
  HTMLInputElement: 'readonly',
  HTMLFormElement: 'readonly',
  HTMLDivElement: 'readonly',
  HTMLButtonElement: 'readonly',
  HTMLAnchorElement: 'readonly',
  Element: 'readonly',
  Node: 'readonly',
  IntersectionObserver: 'readonly',
  ResizeObserver: 'readonly',
  MutationObserver: 'readonly',
  alert: 'readonly',
  confirm: 'readonly',
  btoa: 'readonly',
  atob: 'readonly',
};

/**
 * Shared TypeScript rules — the flat-config translation of the former root
 * .eslintrc.json (eslint:recommended + @typescript-eslint/recommended plus the
 * repo's own overrides). Rule severities are carried over unchanged.
 */
export const typescriptConfig = {
  files: ['**/*.ts', '**/*.tsx', '**/*.mts', '**/*.cts'],
  languageOptions: {
    parser: tsParser,
    ecmaVersion: 'latest',
    sourceType: 'module',
    globals: commonGlobals,
    parserOptions: {
      ecmaFeatures: { jsx: true },
    },
  },
  plugins: {
    '@typescript-eslint': tsPlugin,
  },
  rules: {
    ...js.configs.recommended.rules,
    ...tsPlugin.configs.recommended.rules,
    'no-console': ['warn', { allow: ['error', 'warn'] }],
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-unused-vars': [
      'warn',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/no-require-imports': 'off',
    // TS itself reports undefined identifiers; no-undef duplicates it and
    // misfires on type-only names.
    'no-undef': 'off',
  },
};

/** Plain JS/JSX sources, which must not go through the TS parser. */
export const javascriptConfig = {
  files: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.cjs'],
  languageOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    globals: commonGlobals,
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
  rules: {
    ...js.configs.recommended.rules,
    'no-console': ['warn', { allow: ['error', 'warn'] }],
    'no-undef': 'off',
  },
};

/** Tests may log freely and use `any`. Carried over from the old overrides. */
export const testOverrides = {
  files: [
    '**/*.test.ts',
    '**/*.test.tsx',
    '**/*.spec.ts',
    '**/*.spec.tsx',
    '**/__tests__/**',
    '**/e2e/**',
  ],
  rules: {
    'no-console': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
  },
};

export default [ignores, javascriptConfig, typescriptConfig, testOverrides];
