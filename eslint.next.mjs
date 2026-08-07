// Shared flat-config base for the four Next.js apps.
//
// This is a faithful flat-config translation of `eslint-config-next@15.2.4`'s
// `core-web-vitals` entry point, built directly on the underlying plugins.
//
// It deliberately does NOT go through `eslint-config-next` itself, for two
// reasons:
//   1. eslint-config-next is eslintrc-only. Consuming it from flat config needs
//      FlatCompat from @eslint/eslintrc, which ESLint 10 no longer ships.
//   2. eslint-config-next@15.2.4 peer-caps eslint at "^7 || ^8 || ^9" (still the
//      case through 15.5.x), so it blocks the ESLint 10 upgrade regardless.
//
// Rule set mirrors eslint-config-next/index.js + core-web-vitals.js:
//   react/recommended, react-hooks/recommended, @next/next/recommended,
//   @next/next/core-web-vitals, plus that config's explicit rule overrides.

import nextPlugin from '@next/eslint-plugin-next';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import jsxA11yPlugin from 'eslint-plugin-jsx-a11y';

export const nextCoreWebVitals = {
  files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx', '**/*.mjs'],
  plugins: {
    react: reactPlugin,
    'react-hooks': reactHooksPlugin,
    'jsx-a11y': jsxA11yPlugin,
    '@next/next': nextPlugin,
  },
  settings: {
    react: { version: 'detect' },
  },
  rules: {
    ...reactPlugin.configs.recommended.rules,
    ...reactHooksPlugin.configs.recommended.rules,
    ...nextPlugin.configs.recommended.rules,
    ...nextPlugin.configs['core-web-vitals'].rules,

    // Explicit overrides from eslint-config-next/index.js.
    // `import/no-anonymous-default-export` is intentionally not carried over:
    // eslint-plugin-import is not registered here, and referencing a rule from
    // an unregistered plugin is a hard config error under flat config.
    'react/no-unknown-property': 'off',
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    'react/jsx-no-target-blank': 'off',
    'jsx-a11y/alt-text': ['warn', { elements: ['img'], img: ['Image'] }],
    'jsx-a11y/aria-props': 'warn',
    'jsx-a11y/aria-proptypes': 'warn',
    'jsx-a11y/aria-unsupported-elements': 'warn',
    'jsx-a11y/role-has-required-aria-props': 'warn',
    'jsx-a11y/role-supports-aria-props': 'warn',
  },
};

export default [nextCoreWebVitals];
