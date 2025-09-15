#!/usr/bin/env node

/**
 * Documentation Validation Script
 * Automated checks for documentation quality and consistency
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');
const chalk = require('chalk');

// Configuration
const CONFIG = {
  docsDir: 'docs',
  publicDocsDir: 'apps/docs',
  maxDraftAge: 30, // days
  maxFileSize: 100000, // bytes
  forbiddenPatterns: [
    /api[_-]?key/gi,
    /secret/gi,
    /password/gi,
    /private[_-]?key/gi,
    /token/gi,
  ],
  internalUrls: [
    /localhost/gi,
    /127\.0\.0\.1/gi,
    /internal\./gi,
    /staging\./gi,
  ],
  todoPatterns: [
    /TODO/g,
    /FIXME/g,
    /XXX/g,
    /HACK/g,
  ],
};

// Validation results
let validationResults = {
  passed: 0,
  warnings: 0,
  errors: 0,
  issues: [],
};

// Utility functions
function logHeader(message) {
  console.log(chalk.blue('\n' + '='.repeat(50)));
  console.log(chalk.blue(message));
  console.log(chalk.blue('='.repeat(50)));
}

function logSuccess(message) {
  console.log(chalk.green('✓'), message);
  validationResults.passed++;
}

function logWarning(message, file = null) {
  console.log(chalk.yellow('⚠'), message);
  validationResults.warnings++;
  validationResults.issues.push({ type: 'warning', message, file });
}

function logError(message, file = null) {
  console.log(chalk.red('✗'), message);
  validationResults.errors++;
  validationResults.issues.push({ type: 'error', message, file });
}

// Validation functions
function validateNoDuplicates() {
  logHeader('Checking for Duplicate Content');

  const allFiles = new Map();
  const duplicates = [];

  // Collect all markdown files
  const docFiles = glob.sync(`${CONFIG.docsDir}/**/*.{md,mdx}`, { ignore: '**/node_modules/**' });
  const publicFiles = glob.sync(`${CONFIG.publicDocsDir}/**/*.{md,mdx}`, { ignore: '**/node_modules/**' });

  [...docFiles, ...publicFiles].forEach(file => {
    const basename = path.basename(file);
    if (allFiles.has(basename)) {
      duplicates.push({
        name: basename,
        locations: [allFiles.get(basename), file],
      });
    } else {
      allFiles.set(basename, file);
    }
  });

  if (duplicates.length === 0) {
    logSuccess('No duplicate filenames found');
  } else {
    duplicates.forEach(dup => {
      logWarning(`Duplicate file: ${dup.name}`);
      dup.locations.forEach(loc => console.log(`    - ${loc}`));
    });
  }

  // Check for identical content
  const contentMap = new Map();
  const identicalFiles = [];

  [...docFiles, ...publicFiles].forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const hash = require('crypto').createHash('md5').update(content).digest('hex');

    if (contentMap.has(hash)) {
      identicalFiles.push({
        files: [contentMap.get(hash), file],
        hash,
      });
    } else {
      contentMap.set(hash, file);
    }
  });

  if (identicalFiles.length > 0) {
    identicalFiles.forEach(item => {
      logError(`Files with identical content:`);
      item.files.forEach(file => console.log(`    - ${file}`));
    });
  }
}

function validateNoSensitiveInfo() {
  logHeader('Checking for Sensitive Information');

  const files = glob.sync(`{${CONFIG.docsDir},${CONFIG.publicDocsDir}}/**/*.{md,mdx}`, {
    ignore: '**/node_modules/**',
  });

  let issuesFound = false;

  files.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const lines = content.split('\n');

    CONFIG.forbiddenPatterns.forEach(pattern => {
      lines.forEach((line, index) => {
        if (pattern.test(line)) {
          // Skip if it's in a code comment or documentation about security
          if (!line.includes('```') && !line.includes('//') && !line.includes('#')) {
            logWarning(`Potential sensitive info in ${file}:${index + 1}`, file);
            issuesFound = true;
          }
        }
      });
    });
  });

  if (!issuesFound) {
    logSuccess('No sensitive information detected');
  }
}

function validateNoInternalUrls() {
  logHeader('Checking for Internal URLs');

  const publicFiles = glob.sync(`${CONFIG.publicDocsDir}/**/*.{md,mdx}`, {
    ignore: '**/node_modules/**',
  });

  let issuesFound = false;

  publicFiles.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');

    CONFIG.internalUrls.forEach(pattern => {
      if (pattern.test(content)) {
        logWarning(`Internal URL found in public docs: ${file}`, file);
        issuesFound = true;
      }
    });
  });

  if (!issuesFound) {
    logSuccess('No internal URLs in public documentation');
  }
}

function validateDraftAge() {
  logHeader('Checking Draft Age');

  const draftsDir = path.join(CONFIG.docsDir, 'drafts');

  if (!fs.existsSync(draftsDir)) {
    logSuccess('No drafts directory found');
    return;
  }

  const draftFiles = glob.sync(`${draftsDir}/**/*.{md,mdx}`);
  const now = Date.now();
  let oldDrafts = [];

  draftFiles.forEach(file => {
    const stats = fs.statSync(file);
    const ageInDays = (now - stats.mtimeMs) / (1000 * 60 * 60 * 24);

    if (ageInDays > CONFIG.maxDraftAge) {
      oldDrafts.push({
        file,
        age: Math.floor(ageInDays),
      });
    }
  });

  if (oldDrafts.length === 0) {
    logSuccess('All drafts are recent');
  } else {
    oldDrafts.forEach(draft => {
      logWarning(`Old draft (${draft.age} days): ${draft.file}`, draft.file);
    });
  }
}

function validateBrokenLinks() {
  logHeader('Checking for Broken Links');

  const files = glob.sync(`{${CONFIG.docsDir},${CONFIG.publicDocsDir}}/**/*.{md,mdx}`, {
    ignore: '**/node_modules/**',
  });

  let brokenLinks = [];

  files.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const dir = path.dirname(file);

    // Find all relative links
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let match;

    while ((match = linkRegex.exec(content)) !== null) {
      const linkPath = match[2];

      // Only check relative links
      if (!linkPath.startsWith('http') && !linkPath.startsWith('#')) {
        const absolutePath = path.resolve(dir, linkPath);

        // Check if file exists (with or without .md extension)
        if (
          !fs.existsSync(absolutePath) &&
          !fs.existsSync(absolutePath + '.md') &&
          !fs.existsSync(absolutePath + '.mdx')
        ) {
          brokenLinks.push({
            file,
            link: linkPath,
            text: match[1],
          });
        }
      }
    }
  });

  if (brokenLinks.length === 0) {
    logSuccess('No broken links found');
  } else {
    brokenLinks.forEach(item => {
      logError(`Broken link in ${item.file}: [${item.text}](${item.link})`, item.file);
    });
  }
}

function validateFileSize() {
  logHeader('Checking File Sizes');

  const files = glob.sync(`{${CONFIG.docsDir},${CONFIG.publicDocsDir}}/**/*.{md,mdx}`, {
    ignore: '**/node_modules/**',
  });

  let largeFiles = [];

  files.forEach(file => {
    const stats = fs.statSync(file);
    if (stats.size > CONFIG.maxFileSize) {
      largeFiles.push({
        file,
        size: stats.size,
      });
    }
  });

  if (largeFiles.length === 0) {
    logSuccess('All files are within size limits');
  } else {
    largeFiles.forEach(item => {
      logWarning(
        `Large file (${(item.size / 1024).toFixed(2)} KB): ${item.file}`,
        item.file
      );
    });
  }
}

function validateTodos() {
  logHeader('Checking for TODO Comments');

  const publicFiles = glob.sync(`${CONFIG.publicDocsDir}/**/*.{md,mdx}`, {
    ignore: '**/node_modules/**',
  });

  let todosFound = [];

  publicFiles.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      CONFIG.todoPatterns.forEach(pattern => {
        if (pattern.test(line)) {
          todosFound.push({
            file,
            line: index + 1,
            text: line.trim(),
          });
        }
      });
    });
  });

  if (todosFound.length === 0) {
    logSuccess('No TODO comments in public documentation');
  } else {
    todosFound.forEach(item => {
      logWarning(`TODO in ${item.file}:${item.line}: ${item.text}`, item.file);
    });
  }
}

function validateStructure() {
  logHeader('Checking Documentation Structure');

  // Check for required directories
  const requiredDirs = [
    'docs/internal',
    'docs/drafts',
    'docs/archive',
    'apps/docs/content',
  ];

  requiredDirs.forEach(dir => {
    if (fs.existsSync(dir)) {
      logSuccess(`Required directory exists: ${dir}`);
    } else {
      logError(`Missing required directory: ${dir}`);
    }
  });

  // Check for forbidden directories
  const forbiddenDirs = ['docs/quickstart'];

  forbiddenDirs.forEach(dir => {
    if (fs.existsSync(dir)) {
      logError(`Forbidden directory exists: ${dir} (should be removed)`);
    } else {
      logSuccess(`Forbidden directory absent: ${dir}`);
    }
  });
}

// Generate report
function generateReport() {
  logHeader('Validation Summary');

  const total = validationResults.passed + validationResults.warnings + validationResults.errors;

  console.log(`\nTotal checks: ${total}`);
  console.log(chalk.green(`Passed: ${validationResults.passed}`));
  console.log(chalk.yellow(`Warnings: ${validationResults.warnings}`));
  console.log(chalk.red(`Errors: ${validationResults.errors}`));

  if (validationResults.errors > 0) {
    console.log(chalk.red('\n❌ Validation FAILED'));

    // Write detailed report
    const reportPath = 'docs-validation-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(validationResults, null, 2));
    console.log(`\nDetailed report written to: ${reportPath}`);

    process.exit(1);
  } else if (validationResults.warnings > 0) {
    console.log(chalk.yellow('\n⚠️  Validation passed with warnings'));
  } else {
    console.log(chalk.green('\n✅ Validation PASSED'));
  }
}

// Main execution
function main() {
  console.log(chalk.bold('\n📚 Documentation Validation Suite\n'));

  // Run all validations
  validateStructure();
  validateNoDuplicates();
  validateNoSensitiveInfo();
  validateNoInternalUrls();
  validateDraftAge();
  validateBrokenLinks();
  validateFileSize();
  validateTodos();

  // Generate final report
  generateReport();
}

// Check if required modules are installed
try {
  require('glob');
  require('chalk');
} catch (e) {
  console.error('Required modules not installed. Please run:');
  console.error('npm install glob chalk');
  process.exit(1);
}

// Run validation
main();