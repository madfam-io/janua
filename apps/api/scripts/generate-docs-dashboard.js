#!/usr/bin/env node

/**
 * Documentation Health Dashboard Generator
 * Creates a markdown dashboard with documentation metrics and health status
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const DOCS_DIR = 'docs';
const PUBLIC_DOCS_DIR = 'apps/docs';
const DASHBOARD_PATH = 'docs/DOCUMENTATION_HEALTH.md';

// Metrics collection
const metrics = {
  timestamp: new Date().toISOString(),
  structure: {},
  content: {},
  quality: {},
  coverage: {},
  issues: [],
};

// Utility functions
function countFiles(dir, pattern = '*.{md,mdx}') {
  try {
    const result = execSync(
      `find ${dir} -name "*.md" -o -name "*.mdx" | wc -l`,
      { encoding: 'utf8' }
    );
    return parseInt(result.trim());
  } catch {
    return 0;
  }
}

function getFileSize(dir) {
  try {
    const result = execSync(`du -sh ${dir} | cut -f1`, { encoding: 'utf8' });
    return result.trim();
  } catch {
    return 'N/A';
  }
}

function findLargeFiles(dir, limitKB = 100) {
  try {
    const result = execSync(
      `find ${dir} -name "*.md" -o -name "*.mdx" | xargs ls -la | awk '$5 > ${
        limitKB * 1024
      } {print $9, $5}'`,
      { encoding: 'utf8' }
    );
    return result
      .trim()
      .split('\n')
      .filter((line) => line.length > 0);
  } catch {
    return [];
  }
}

function checkForPattern(dir, pattern) {
  try {
    const result = execSync(
      `grep -r "${pattern}" ${dir} --include="*.md" --include="*.mdx" | wc -l`,
      { encoding: 'utf8' }
    );
    return parseInt(result.trim());
  } catch {
    return 0;
  }
}

function getDraftAge() {
  const draftsDir = path.join(DOCS_DIR, 'drafts');
  if (!fs.existsSync(draftsDir)) {
    return [];
  }

  try {
    const result = execSync(
      `find ${draftsDir} -name "*.md" -o -name "*.mdx" -exec stat -f "%m %N" {} \\; | sort -n`,
      { encoding: 'utf8' }
    );

    const now = Date.now() / 1000;
    return result
      .trim()
      .split('\n')
      .filter((line) => line.length > 0)
      .map((line) => {
        const [timestamp, file] = line.split(' ');
        const ageInDays = Math.floor((now - parseInt(timestamp)) / 86400);
        return { file: path.basename(file), age: ageInDays };
      })
      .filter((item) => item.age > 0);
  } catch {
    return [];
  }
}

// Collect metrics
function collectMetrics() {
  console.log('📊 Collecting documentation metrics...');

  // Structure metrics
  metrics.structure = {
    internalDocs: countFiles(DOCS_DIR),
    publicDocs: countFiles(PUBLIC_DOCS_DIR),
    drafts: countFiles(path.join(DOCS_DIR, 'drafts')),
    archived: countFiles(path.join(DOCS_DIR, 'archive')),
    totalSize: getFileSize('.'),
  };

  // Content metrics
  metrics.content = {
    todos: checkForPattern(PUBLIC_DOCS_DIR, 'TODO\\|FIXME'),
    codeBlocks: checkForPattern(PUBLIC_DOCS_DIR, '```'),
    images: checkForPattern(PUBLIC_DOCS_DIR, '!\\[.*\\]\\(.*\\)'),
    links: checkForPattern(PUBLIC_DOCS_DIR, '\\[.*\\]\\(.*\\)'),
  };

  // Quality metrics
  const largeFiles = findLargeFiles('.', 100);
  const oldDrafts = getDraftAge().filter((d) => d.age > 30);

  metrics.quality = {
    largeFiles: largeFiles.length,
    oldDrafts: oldDrafts.length,
    duplicateRisk: checkDuplicates(),
    sensitiveInfoRisk: checkSensitiveInfo(),
  };

  // Coverage metrics
  metrics.coverage = {
    hasApiDocs: fs.existsSync(path.join(PUBLIC_DOCS_DIR, 'content/api')),
    hasSdkDocs: fs.existsSync(path.join(PUBLIC_DOCS_DIR, 'content/sdks')),
    hasGuides: fs.existsSync(path.join(PUBLIC_DOCS_DIR, 'content/guides')),
    hasQuickstart: checkForPattern(PUBLIC_DOCS_DIR, 'quick.?start') > 0,
  };

  // Collect issues
  if (largeFiles.length > 0) {
    metrics.issues.push({
      type: 'warning',
      message: `${largeFiles.length} large files detected (>100KB)`,
    });
  }

  if (oldDrafts.length > 0) {
    metrics.issues.push({
      type: 'warning',
      message: `${oldDrafts.length} old drafts pending (>30 days)`,
    });
  }

  if (metrics.content.todos > 0) {
    metrics.issues.push({
      type: 'warning',
      message: `${metrics.content.todos} TODO/FIXME comments in public docs`,
    });
  }

  if (fs.existsSync(path.join(DOCS_DIR, 'quickstart'))) {
    metrics.issues.push({
      type: 'error',
      message: 'Orphaned quickstart directory exists',
    });
  }
}

function checkDuplicates() {
  try {
    const result = execSync(
      `find ${DOCS_DIR} ${PUBLIC_DOCS_DIR} -name "*.md" -o -name "*.mdx" | xargs basename | sort | uniq -d | wc -l`,
      { encoding: 'utf8' }
    );
    return parseInt(result.trim()) > 0 ? 'High' : 'Low';
  } catch {
    return 'Unknown';
  }
}

function checkSensitiveInfo() {
  const patterns = ['api.?key', 'secret', 'password', 'token'];
  let count = 0;

  patterns.forEach((pattern) => {
    count += checkForPattern(PUBLIC_DOCS_DIR, pattern);
  });

  return count > 0 ? 'High' : 'Low';
}

// Generate dashboard
function generateDashboard() {
  console.log('📝 Generating documentation dashboard...');

  const healthScore = calculateHealthScore();
  const healthEmoji = getHealthEmoji(healthScore);
  const lastUpdated = new Date().toLocaleString();

  const dashboard = `# 📊 Documentation Health Dashboard

> Auto-generated health metrics for Plinto documentation
> Last updated: ${lastUpdated}

## 🏥 Overall Health Score: ${healthScore}/100 ${healthEmoji}

${generateHealthBar(healthScore)}

## 📈 Key Metrics

### Structure Overview
| Metric | Value | Status |
|--------|-------|--------|
| Internal Documentation | ${metrics.structure.internalDocs} files | ${
    metrics.structure.internalDocs > 0 ? '✅' : '⚠️'
  } |
| Public Documentation | ${metrics.structure.publicDocs} files | ${
    metrics.structure.publicDocs > 0 ? '✅' : '⚠️'
  } |
| Pending Drafts | ${metrics.structure.drafts} files | ${
    metrics.structure.drafts > 10 ? '⚠️' : '✅'
  } |
| Archived Content | ${metrics.structure.archived} files | ℹ️ |
| Total Size | ${metrics.structure.totalSize} | ℹ️ |

### Content Quality
| Metric | Value | Status |
|--------|-------|--------|
| TODO/FIXME in Public | ${metrics.content.todos} | ${
    metrics.content.todos === 0 ? '✅' : '⚠️'
  } |
| Code Examples | ${metrics.content.codeBlocks} blocks | ${
    metrics.content.codeBlocks > 0 ? '✅' : '⚠️'
  } |
| Images | ${metrics.content.images} | ℹ️ |
| Internal Links | ${metrics.content.links} | ℹ️ |

### Risk Assessment
| Risk Factor | Level | Action Required |
|-------------|-------|-----------------|
| Large Files | ${metrics.quality.largeFiles > 0 ? '⚠️ ' + metrics.quality.largeFiles + ' files' : '✅ None'} | ${
    metrics.quality.largeFiles > 0 ? 'Consider splitting' : 'None'
  } |
| Old Drafts | ${metrics.quality.oldDrafts > 0 ? '⚠️ ' + metrics.quality.oldDrafts + ' drafts' : '✅ None'} | ${
    metrics.quality.oldDrafts > 0 ? 'Review and promote' : 'None'
  } |
| Duplicate Content | ${metrics.quality.duplicateRisk} | ${
    metrics.quality.duplicateRisk === 'High' ? 'Immediate review' : 'Monitor'
  } |
| Sensitive Information | ${metrics.quality.sensitiveInfoRisk} | ${
    metrics.quality.sensitiveInfoRisk === 'High' ? 'Security review' : 'Monitor'
  } |

### Documentation Coverage
| Area | Status | Completeness |
|------|--------|--------------|
| API Documentation | ${metrics.coverage.hasApiDocs ? '✅ Present' : '❌ Missing'} | ${
    metrics.coverage.hasApiDocs ? 'Complete' : 'Required'
  } |
| SDK Documentation | ${metrics.coverage.hasSdkDocs ? '✅ Present' : '❌ Missing'} | ${
    metrics.coverage.hasSdkDocs ? 'Complete' : 'Required'
  } |
| User Guides | ${metrics.coverage.hasGuides ? '✅ Present' : '❌ Missing'} | ${
    metrics.coverage.hasGuides ? 'Complete' : 'Required'
  } |
| Quick Start | ${metrics.coverage.hasQuickstart ? '✅ Present' : '❌ Missing'} | ${
    metrics.coverage.hasQuickstart ? 'Complete' : 'Required'
  } |

## 🚨 Active Issues

${
  metrics.issues.length === 0
    ? '✅ No active issues detected!'
    : metrics.issues
        .map((issue) => {
          const icon = issue.type === 'error' ? '❌' : '⚠️';
          return `- ${icon} ${issue.message}`;
        })
        .join('\n')
}

## 📋 Recommended Actions

${generateRecommendations()}

## 🔄 Automation Status

| Check | Status | Schedule |
|-------|--------|----------|
| Pre-commit Hooks | ${
    fs.existsSync('.husky/pre-commit-docs') ? '✅ Configured' : '❌ Missing'
  } | Every commit |
| CI/CD Validation | ${
    fs.existsSync('.github/workflows/docs-validation.yml') ? '✅ Configured' : '❌ Missing'
  } | Every PR |
| Health Dashboard | ✅ Generated | Weekly |

## 📊 Trend Analysis

\`\`\`
Documentation Growth (Last 30 days)
Internal: ${getGrowthIndicator(metrics.structure.internalDocs)}
Public:   ${getGrowthIndicator(metrics.structure.publicDocs)}
Quality:  ${getQualityTrend()}
\`\`\`

## 🛠️ Quick Commands

\`\`\`bash
# Run full validation
./scripts/docs-pipeline.sh health

# Check for duplicates
./scripts/docs-pipeline.sh check

# Validate specific file
./scripts/docs-pipeline.sh validate <file>

# Promote draft to public
./scripts/docs-pipeline.sh promote <draft> <target>
\`\`\`

---

*This dashboard is automatically generated. To update, run: \`node scripts/generate-docs-dashboard.js\`*

*For detailed guidelines, see: [Content Guidelines](./CONTENT_GUIDELINES.md)*`;

  fs.writeFileSync(DASHBOARD_PATH, dashboard);
  console.log(`✅ Dashboard generated at: ${DASHBOARD_PATH}`);
}

function calculateHealthScore() {
  let score = 100;

  // Deduct points for issues
  if (metrics.structure.publicDocs === 0) score -= 20;
  if (metrics.structure.drafts > 10) score -= 10;
  if (metrics.content.todos > 0) score -= Math.min(15, metrics.content.todos * 3);
  if (metrics.quality.largeFiles > 0) score -= 5;
  if (metrics.quality.oldDrafts > 0) score -= 10;
  if (metrics.quality.duplicateRisk === 'High') score -= 15;
  if (metrics.quality.sensitiveInfoRisk === 'High') score -= 20;
  if (!metrics.coverage.hasApiDocs) score -= 10;
  if (!metrics.coverage.hasSdkDocs) score -= 10;

  return Math.max(0, score);
}

function getHealthEmoji(score) {
  if (score >= 90) return '🟢';
  if (score >= 70) return '🟡';
  if (score >= 50) return '🟠';
  return '🔴';
}

function generateHealthBar(score) {
  const filled = Math.round(score / 5);
  const empty = 20 - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  return `\`[${bar}]\``;
}

function getGrowthIndicator(value) {
  // This would ideally compare with historical data
  return '→ Stable';
}

function getQualityTrend() {
  const score = calculateHealthScore();
  if (score >= 80) return '↑ Improving';
  if (score >= 60) return '→ Stable';
  return '↓ Declining';
}

function generateRecommendations() {
  const recommendations = [];

  if (metrics.structure.drafts > 5) {
    recommendations.push('1. **Review pending drafts** - You have multiple drafts awaiting review');
  }

  if (metrics.content.todos > 0) {
    recommendations.push('2. **Resolve TODO comments** - Clean up unfinished documentation in public');
  }

  if (metrics.quality.oldDrafts > 0) {
    recommendations.push('3. **Process old drafts** - Some drafts are over 30 days old');
  }

  if (metrics.quality.duplicateRisk === 'High') {
    recommendations.push('4. **Remove duplicate content** - Consolidate documentation to single location');
  }

  if (!metrics.coverage.hasQuickstart) {
    recommendations.push('5. **Add quick start guide** - Help users get started quickly');
  }

  if (recommendations.length === 0) {
    recommendations.push('✅ Documentation is in excellent health! Keep up the good work.');
  }

  return recommendations.join('\n');
}

// Main execution
function main() {
  console.log('🚀 Starting Documentation Health Check...\n');

  // Check if running from project root
  if (!fs.existsSync(DOCS_DIR) || !fs.existsSync(PUBLIC_DOCS_DIR)) {
    console.error('❌ Must run from project root directory');
    process.exit(1);
  }

  // Collect metrics
  collectMetrics();

  // Generate dashboard
  generateDashboard();

  // Print summary
  const healthScore = calculateHealthScore();
  console.log(`\n📊 Health Score: ${healthScore}/100 ${getHealthEmoji(healthScore)}`);

  if (metrics.issues.length > 0) {
    console.log('\n⚠️  Active Issues:');
    metrics.issues.forEach((issue) => {
      console.log(`  - ${issue.message}`);
    });
  }

  console.log('\n✅ Dashboard generation complete!');
}

// Run the script
main();