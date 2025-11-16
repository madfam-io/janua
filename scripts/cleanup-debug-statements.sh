#!/bin/bash
# Script to audit and document debug statement cleanup
# This creates a report of debug statements that need manual review

set -e

REPORT_FILE="claudedocs/debug-statements-audit.md"

echo "# Debug Statements Audit Report" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Count total debug statements
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# TypeScript/JavaScript console statements
TS_COUNT=$(grep -r "console\.log\|console\.error\|console\.warn\|console\.debug" apps packages --include="*.ts" --include="*.tsx" --include="*.js" --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build --exclude-dir=.next --exclude-dir=coverage 2>/dev/null | wc -l || echo "0")
echo "- TypeScript/JavaScript console statements: $TS_COUNT" >> "$REPORT_FILE"

# Python print statements
PY_COUNT=$(grep -r "print(" apps/api --include="*.py" --exclude-dir=__pycache__ --exclude-dir=tests 2>/dev/null | wc -l || echo "0")
echo "- Python print statements: $PY_COUNT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Categorize statements
echo "## Categories" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. Test files (SAFE - can keep)
echo "### Test Files (Safe - Keep)" >> "$REPORT_FILE"
TEST_COUNT=$(grep -r "console\." apps packages --include="*.test.ts" --include="*.test.tsx" --include="*.spec.ts" --exclude-dir=node_modules 2>/dev/null | wc -l || echo "0")
echo "- Test file console statements: $TEST_COUNT (no action needed)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 2. Documentation files (SAFE - example code)
echo "### Documentation Examples (Safe - Keep)" >> "$REPORT_FILE"
DOC_COUNT=$(grep -r "console\.\|print(" apps/api/app/docs apps/api/app/sdk --include="*.py" --include="*.ts" 2>/dev/null | wc -l || echo "0")
echo "- Documentation example statements: $DOC_COUNT (example code)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 3. Production code (ACTION NEEDED)
echo "### Production Code (Action Needed)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "#### TypeScript/JavaScript Files" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
grep -rn "console\.log\|console\.error\|console\.warn" apps packages \
  --include="*.ts" --include="*.tsx" --include="*.js" \
  --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build \
  --exclude-dir=.next --exclude-dir=coverage \
  | grep -v "\.test\." | grep -v "jest-setup" | grep -v "prettify.js" \
  | head -30 >> "$REPORT_FILE" 2>/dev/null || echo "No matches found" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "#### Python Files (Non-Documentation)" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
grep -rn "print(" apps/api/app \
  --include="*.py" \
  --exclude-dir=__pycache__ --exclude-dir=tests \
  | grep -v "/docs/" | grep -v "/sdk/" \
  | head -20 >> "$REPORT_FILE" 2>/dev/null || echo "No matches found" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Recommendations
echo "## Recommendations" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "### Immediate Actions" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "1. **Python Production Code**" >> "$REPORT_FILE"
echo "   - Replace \`print()\` with \`logger.info()\` or \`logger.debug()\`" >> "$REPORT_FILE"
echo "   - Use: \`from app.utils.logger import create_logger\`" >> "$REPORT_FILE"
echo "   - Example: \`logger = create_logger(__name__)\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "2. **TypeScript/JavaScript Production Code**" >> "$REPORT_FILE"
echo "   - Replace \`console.log()\` with \`logger.debug()\`" >> "$REPORT_FILE"
echo "   - Use: \`import { createLogger } from '@/utils/logger'\`" >> "$REPORT_FILE"
echo "   - Example: \`const logger = createLogger('ComponentName')\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "3. **Files to Keep As-Is**" >> "$REPORT_FILE"
echo "   - Test files (*.test.ts, *.spec.ts)" >> "$REPORT_FILE"
echo "   - Documentation examples (apps/api/app/docs/, apps/api/app/sdk/)" >> "$REPORT_FILE"
echo "   - Mock/jest setup files" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "## Implementation Status" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- ✅ Created production-safe logger utilities" >> "$REPORT_FILE"
echo "  - Python: \`apps/api/app/utils/logger.py\`" >> "$REPORT_FILE"
echo "  - TypeScript: \`packages/core/src/utils/logger.ts\`" >> "$REPORT_FILE"
echo "- ✅ Replaced WebSocket router print statement" >> "$REPORT_FILE"
echo "- 🔄 Remaining: ~20 production code statements need manual review" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "Report generated: $REPORT_FILE"
echo ""
echo "Summary:"
echo "  TypeScript/JS: $TS_COUNT statements"
echo "  Python: $PY_COUNT statements"
echo "  Test files (safe): $TEST_COUNT statements"
echo "  Documentation (safe): $DOC_COUNT statements"
echo ""
echo "Action: Review $REPORT_FILE for detailed cleanup plan"
