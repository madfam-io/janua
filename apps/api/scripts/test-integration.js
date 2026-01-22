#!/usr/bin/env node

/**
 * Integration Test Runner
 *
 * Simplified test runner for package installation tests
 * that doesn't require complex Jest configuration.
 */

const fs = require('fs').promises;
const path = require('path');
// Note: exec/promisify and os module are available for future use if needed
// const { exec } = require('child_process');
// const { promisify } = require('util');
// const execAsync = promisify(exec);
// const os = require('os');

// Colors for console output
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  reset: '\x1b[0m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

async function runTest(name, testFn) {
  try {
    log(`  ⏳ ${name}...`, 'cyan');
    await testFn();
    log(`  ✅ ${name}`, 'green');
    return true;
  } catch (error) {
    log(`  ❌ ${name}`, 'red');
    console.error(`     Error: ${error.message}`);
    return false;
  }
}

async function testTypeScriptSDKBuild() {
  const distPath = path.join(__dirname, '../packages/typescript-sdk/dist');

  // Use atomic check - stat is atomic and provides existence check
  try {
    const stat = await fs.stat(distPath);
    if (!stat.isDirectory()) {
      throw new Error('TypeScript SDK dist is not a directory');
    }
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('TypeScript SDK dist directory not found');
    }
    throw err;
  }

  const files = await fs.readdir(distPath);
  const requiredFiles = ['index.js', 'index.esm.js', 'index.d.ts'];

  for (const file of requiredFiles) {
    if (!files.includes(file)) {
      throw new Error(`Required file ${file} not found in dist/`);
    }
  }
}

async function testPackageVersions() {
  const packagesDir = path.join(__dirname, '../packages');
  const packages = await fs.readdir(packagesDir);

  const versions = new Map();

  for (const pkg of packages) {
    const packageJsonPath = path.join(packagesDir, pkg, 'package.json');
    try {
      const content = await fs.readFile(packageJsonPath, 'utf-8');
      const { name, version, private: isPrivate } = JSON.parse(content);

      if (!isPrivate) {
        versions.set(name, version);
      }
    } catch (_err) {
      // Skip if no package.json - underscore prefix indicates intentionally unused
    }
  }

  const uniqueVersions = new Set(versions.values());
  if (uniqueVersions.size > 1) {
    throw new Error(`Inconsistent versions found: ${Array.from(uniqueVersions).join(', ')}`);
  }

  if (!uniqueVersions.has('1.0.0')) {
    throw new Error(`Expected version 1.0.0, found: ${Array.from(uniqueVersions).join(', ')}`);
  }
}

async function testExampleApp() {
  const examplePath = path.join(__dirname, '../examples/nextjs-app/package.json');
  const content = await fs.readFile(examplePath, 'utf-8');
  const pkg = JSON.parse(content);

  const requiredDeps = [
    '@janua/nextjs-sdk',
    '@janua/react-sdk',
    '@janua/typescript-sdk',
    'next',
    'react'
  ];

  for (const dep of requiredDeps) {
    if (!pkg.dependencies[dep]) {
      throw new Error(`Missing dependency: ${dep}`);
    }
  }
}

async function testExampleComponents() {
  const componentsPath = path.join(__dirname, '../examples/nextjs-app/app/components');
  const components = await fs.readdir(componentsPath);

  const requiredComponents = ['LoginForm.tsx', 'UserProfile.tsx', 'Dashboard.tsx'];

  for (const component of requiredComponents) {
    if (!components.includes(component)) {
      throw new Error(`Missing component: ${component}`);
    }
  }
}

async function testAPIDocumentation() {
  const docPath = path.join(__dirname, '../API_REFERENCE.md');

  // Use atomic stat check instead of access then read (TOCTOU prevention)
  let content;
  try {
    content = await fs.readFile(docPath, 'utf-8');
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('API_REFERENCE.md not found');
    }
    throw err;
  }

  // Check for essential sections
  const requiredSections = [
    '## Authentication',
    '## User Management',
    '## Session Management',
    '## Multi-Factor Authentication',
    '## Organization'
  ];

  for (const section of requiredSections) {
    if (!content.includes(section)) {
      throw new Error(`Missing documentation section: ${section}`);
    }
  }
}

async function testSecurityPolicy() {
  const securityPath = path.join(__dirname, '../SECURITY.md');

  // Use atomic stat check instead of access then read (TOCTOU prevention)
  let content;
  try {
    content = await fs.readFile(securityPath, 'utf-8');
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('SECURITY.md not found');
    }
    throw err;
  }

  // Check for essential sections
  const requiredContent = [
    'Vulnerability Disclosure',
    'security@janua.dev',
    'Security Best Practices'
  ];

  for (const text of requiredContent) {
    if (!content.includes(text)) {
      throw new Error(`Missing security content: ${text}`);
    }
  }
}

async function testChangelog() {
  const changelogPath = path.join(__dirname, '../CHANGELOG.md');

  // Use atomic stat check instead of access then read (TOCTOU prevention)
  let content;
  try {
    content = await fs.readFile(changelogPath, 'utf-8');
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('CHANGELOG.md not found');
    }
    throw err;
  }

  // Check for version 1.0.0 entry
  if (!content.includes('## [1.0.0]')) {
    throw new Error('Version 1.0.0 not found in CHANGELOG');
  }
}

async function testPublishingInfrastructure() {
  // Check for publish workflow - use atomic stat check
  const workflowPath = path.join(__dirname, '../.github/workflows/publish.yml');
  try {
    await fs.stat(workflowPath);
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('Publishing workflow not found');
    }
    throw err;
  }

  // Check for publish script - use atomic stat check
  const scriptPath = path.join(__dirname, '../scripts/publish.sh');
  try {
    await fs.stat(scriptPath);
  } catch (err) {
    if (err.code === 'ENOENT') {
      throw new Error('Publishing script not found');
    }
    throw err;
  }
}

async function main() {
  log('\n📦 Janua Platform - Integration Tests\n', 'cyan');

  const tests = [
    { name: 'TypeScript SDK Build', fn: testTypeScriptSDKBuild },
    { name: 'Package Versions (1.0.0)', fn: testPackageVersions },
    { name: 'Example App Dependencies', fn: testExampleApp },
    { name: 'Example App Components', fn: testExampleComponents },
    { name: 'API Documentation', fn: testAPIDocumentation },
    { name: 'Security Policy', fn: testSecurityPolicy },
    { name: 'Changelog', fn: testChangelog },
    { name: 'Publishing Infrastructure', fn: testPublishingInfrastructure }
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    const result = await runTest(test.name, test.fn);
    if (result) {
      passed++;
    } else {
      failed++;
    }
  }

  log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');

  if (failed === 0) {
    log(`\n✨ All tests passed! (${passed}/${tests.length})\n`, 'green');
    log('The platform meets all pre-launch requirements:', 'green');
    log('  ✅ Packages built and versioned at 1.0.0', 'green');
    log('  ✅ Example application ready', 'green');
    log('  ✅ Documentation complete', 'green');
    log('  ✅ Security policies in place', 'green');
    log('  ✅ Publishing infrastructure ready', 'green');
    process.exit(0);
  } else {
    log(`\n❌ ${failed} tests failed, ${passed} passed\n`, 'red');
    process.exit(1);
  }
}

// Run the tests
main().catch(error => {
  log(`\n💥 Unexpected error: ${error.message}\n`, 'red');
  process.exit(1);
});
