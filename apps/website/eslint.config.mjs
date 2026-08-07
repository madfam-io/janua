// Flat config for @janua/website. Replaces .eslintrc.json
// (extends next/core-web-vitals; react/no-unescaped-entities off).

import { ignores, javascriptConfig, typescriptConfig, testOverrides } from '../../eslint.config.mjs';
import { nextCoreWebVitals } from '../../eslint.next.mjs';

export default [
  ignores,
  javascriptConfig,
  typescriptConfig,
  nextCoreWebVitals,
  {
    rules: {
      'react/no-unescaped-entities': 'off',
    },
  },
  {
    files: ['app/demo/**/*', 'e2e/**/*'],
    rules: {
      'no-console': 'off',
    },
  },
  testOverrides,
];
