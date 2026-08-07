// Flat config for @janua/typescript-sdk. Replaces .eslintrc.cjs.
//
// The eslintrc file applied eslint:recommended to everything and then, in a
// `**/*.ts,tsx` override, swapped no-unused-vars for its @typescript-eslint
// counterpart. Flat config expresses that as two file-scoped blocks.

import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import { ignores, commonGlobals } from '../../eslint.config.mjs';

export default [
  ignores,
  // Test sources were excluded via --ignore-pattern on the old lint script;
  // expressing it here lets the script be a plain `eslint .`.
  { ignores: ['**/__tests__/**', '**/*.test.ts', '**/*.test.tsx'] },
  {
    files: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.cjs'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: commonGlobals,
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
      'no-console': 'warn',
      'no-undef': 'off',
    },
  },
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: commonGlobals,
    },
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      ...js.configs.recommended.rules,
      'prefer-const': 'error',
      'no-var': 'error',
      'no-console': 'warn',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-undef': 'off',
    },
  },
];
