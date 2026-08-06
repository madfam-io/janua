// NOTE: previously `const { defaults } = require('jest-config')` — jest-config
// is never a direct dependency anywhere in this monorepo (only `jest`, whose
// bundled jest-config isn't hoisted for a plain require() from a root-level
// preset file), so every package extending this preset failed at load time
// with MODULE_NOT_FOUND before running a single test. Jest's own default
// moduleFileExtensions is a stable, documented list — inlined here instead of
// adding a phantom top-level dependency just to read one constant.
const JEST_DEFAULT_MODULE_FILE_EXTENSIONS = [
  'js', 'mjs', 'cjs', 'jsx', 'ts', 'tsx', 'json', 'node',
];

module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  
  // Common setup - apps should override this with their specific setup files
  setupFilesAfterEnv: [],
  
  // Module resolution
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@janua/(.*)$': '<rootDir>/../../packages/$1/src',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': 'jest-transform-stub'
  },

  // Test patterns
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/dist/',
    '/build/',
  ],
  
  // Transform settings
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      useESM: false,
      isolatedModules: true,
      tsconfig: {
        jsx: 'react-jsx',
      },
    }],
    '^.+\\.(js|jsx)$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', { targets: { node: 'current' } }],
        ['@babel/preset-react', { runtime: 'automatic' }],
        '@babel/preset-typescript',
      ],
    }],
  },
  
  // Coverage
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/jest.config.js',
    '!**/next.config.js',
    '!**/postcss.config.js',
    '!**/tailwind.config.{js,ts}',
    '!**/dist/**',
    '!**/build/**',
  ],
  
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },

  // Test timeout
  testTimeout: 10000,

  // Other Jest settings
  verbose: true,
  bail: false,
  
  // Module file extensions
  moduleFileExtensions: [...JEST_DEFAULT_MODULE_FILE_EXTENSIONS, 'ts', 'tsx'],
  
  // Resolver
  resolver: undefined,

  // Global setup
  globalSetup: undefined,
  globalTeardown: undefined,

  // Error handling
  errorOnDeprecated: false,
  
  // Performance
  maxWorkers: '50%',
};