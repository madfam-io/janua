#!/bin/bash
# Generate CHANGELOG.md from conventional commits
# Usage: ./generate-changelog.sh <sdk-name> [--output <file>]

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
SDK_NAME=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            SDK_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$SDK_NAME" ]; then
    echo "Usage: $0 <sdk-name> [--output <file>]"
    exit 1
fi

if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="packages/$SDK_NAME/CHANGELOG.md"
fi

echo -e "${BLUE}📝 Generating changelog for $SDK_NAME${NC}"
echo ""

# Get all tags for this SDK
TAGS=$(git tag -l "${SDK_NAME}-v*" | sort -V)

if [ -z "$TAGS" ]; then
    echo -e "${YELLOW}⚠️  No tags found for $SDK_NAME${NC}"
    echo -e "${YELLOW}   Creating changelog from all commits${NC}"
    TAGS="HEAD"
fi

# Initialize changelog
cat > "$OUTPUT_FILE" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

EOF

# Process each tag
PREVIOUS_TAG=""

while IFS= read -r TAG; do
    if [ -z "$PREVIOUS_TAG" ]; then
        # First tag - all commits up to this tag
        VERSION=$(echo "$TAG" | sed "s/${SDK_NAME}-v//")
        DATE=$(git log -1 --format=%ai "$TAG" | cut -d' ' -f1)
        COMMITS=$(git log "$TAG" --oneline --no-merges 2>/dev/null || echo "")
    else
        # Commits between tags
        VERSION=$(echo "$TAG" | sed "s/${SDK_NAME}-v//")
        DATE=$(git log -1 --format=%ai "$TAG" | cut -d' ' -f1)
        COMMITS=$(git log "${PREVIOUS_TAG}..${TAG}" --oneline --no-merges 2>/dev/null || echo "")
    fi
    
    # Add version header
    echo "" >> "$OUTPUT_FILE"
    echo "## [$VERSION] - $DATE" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Categorize commits
    FEATURES=""
    FIXES=""
    BREAKING=""
    OTHER=""
    
    while IFS= read -r commit; do
        [ -z "$commit" ] && continue
        
        MESSAGE=$(echo "$commit" | cut -d' ' -f2-)
        HASH=$(echo "$commit" | cut -d' ' -f1)
        
        if echo "$MESSAGE" | grep -qiE "BREAKING[ -]CHANGE|^[a-z]+!:"; then
            BREAKING="${BREAKING}\n- $MESSAGE ($HASH)"
        elif echo "$MESSAGE" | grep -qiE "^feat(\(.+\))?:"; then
            FEATURES="${FEATURES}\n- $(echo "$MESSAGE" | sed 's/^feat(\([^)]*\)): *//')" 
        elif echo "$MESSAGE" | grep -qiE "^fix(\(.+\))?:"; then
            FIXES="${FIXES}\n- $(echo "$MESSAGE" | sed 's/^fix(\([^)]*\)): *//')"
        elif echo "$MESSAGE" | grep -qiE "^(perf|build|refactor)(\(.+\))?:"; then
            OTHER="${OTHER}\n- $MESSAGE"
        fi
    done <<< "$COMMITS"
    
    # Write categorized changes
    if [ -n "$BREAKING" ]; then
        echo "### ⚠️ BREAKING CHANGES" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo -e "$BREAKING" | grep -v '^$' >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "$FEATURES" ]; then
        echo "### ✨ Features" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo -e "$FEATURES" | grep -v '^$' >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "$FIXES" ]; then
        echo "### 🐛 Bug Fixes" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo -e "$FIXES" | grep -v '^$' >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    if [ -n "$OTHER" ]; then
        echo "### 🔧 Other Changes" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo -e "$OTHER" | grep -v '^$' >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    
    PREVIOUS_TAG="$TAG"
done <<< "$TAGS"

echo -e "${GREEN}✅ Changelog generated: $OUTPUT_FILE${NC}"
