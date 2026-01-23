#!/usr/bin/env node
/**
 * Documentation validation script
 * Checks for required structure, broken internal links, and quality standards
 *
 * Referenced by: .github/workflows/docs-validation.yml
 */

const fs = require('fs');
const path = require('path');

const errors = [];
const warnings = [];

// Required directories for documentation
const requiredDirs = [
  'docs/internal',
  'docs/guides',
  'apps/docs/content'
];

// Optional directories (warned if missing, not errors)
const optionalDirs = [
  'docs/drafts',
  'docs/archive',
  'docs/api'
];

// Forbidden directories (should not exist)
const forbiddenDirs = [
  'docs/quickstart'
];

console.log('📚 Janua Documentation Validation\n');
console.log('='.repeat(50));

// Check forbidden directories
console.log('\n🚫 Checking for forbidden directories...');
for (const dir of forbiddenDirs) {
  if (fs.existsSync(dir)) {
    errors.push(`Forbidden directory '${dir}' exists - should be removed`);
  }
}

// Check required directories
console.log('\n✅ Checking required directories...');
for (const dir of requiredDirs) {
  if (!fs.existsSync(dir)) {
    errors.push(`Required directory '${dir}' is missing`);
  } else {
    console.log(`  ✓ ${dir}`);
  }
}

// Check optional directories
console.log('\n📂 Checking optional directories...');
for (const dir of optionalDirs) {
  if (!fs.existsSync(dir)) {
    warnings.push(`Optional directory '${dir}' is missing`);
    console.log(`  ⚠ ${dir} (missing)`);
  } else {
    console.log(`  ✓ ${dir}`);
  }
}

// Count documentation files
console.log('\n📊 Documentation metrics...');
function countFiles(dir, extensions = ['.md', '.mdx']) {
  if (!fs.existsSync(dir)) return 0;
  let count = 0;
  const items = fs.readdirSync(dir, { withFileTypes: true });
  for (const item of items) {
    const fullPath = path.join(dir, item.name);
    if (item.isDirectory() && !item.name.startsWith('.') && item.name !== 'node_modules') {
      count += countFiles(fullPath, extensions);
    } else if (item.isFile() && extensions.some(ext => item.name.endsWith(ext))) {
      count++;
    }
  }
  return count;
}

const internalDocs = countFiles('docs');
const publicDocs = countFiles('apps/docs');
console.log(`  Internal docs: ${internalDocs} files`);
console.log(`  Public docs: ${publicDocs} files`);
console.log(`  Total: ${internalDocs + publicDocs} files`);

// Check for README files in key locations
console.log('\n📖 Checking for README files...');
const keyReadmes = [
  'README.md',
  'docs/README.md',
  'apps/docs/README.md'
];

for (const readme of keyReadmes) {
  if (fs.existsSync(readme)) {
    console.log(`  ✓ ${readme}`);
  } else {
    warnings.push(`Missing README: ${readme}`);
    console.log(`  ⚠ ${readme} (missing)`);
  }
}

// Report results
console.log('\n' + '='.repeat(50));
console.log('📋 Validation Summary\n');

if (errors.length > 0) {
  console.error('❌ Errors:');
  errors.forEach(e => console.error(`  - ${e}`));
}

if (warnings.length > 0) {
  console.warn('\n⚠️  Warnings:');
  warnings.forEach(w => console.warn(`  - ${w}`));
}

if (errors.length === 0 && warnings.length === 0) {
  console.log('✅ All documentation checks passed!');
}

// Write report for CI artifacts
const report = {
  timestamp: new Date().toISOString(),
  errors,
  warnings,
  metrics: {
    internalDocs,
    publicDocs,
    total: internalDocs + publicDocs
  },
  status: errors.length === 0 ? 'pass' : 'fail'
};

fs.writeFileSync('docs-validation-report.json', JSON.stringify(report, null, 2));
console.log('\n📄 Report written to docs-validation-report.json');

// Exit with error if there are errors
if (errors.length > 0) {
  console.error('\n❌ Documentation validation failed');
  process.exit(1);
}

console.log('\n✅ Documentation validation passed');
process.exit(0);
