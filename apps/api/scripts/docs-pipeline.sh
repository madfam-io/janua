#!/bin/bash

# Documentation Pipeline Management Script
# Purpose: Manage content flow from draft to publication with validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
DOCS_DIR="docs"
DRAFTS_DIR="$DOCS_DIR/drafts"
PUBLIC_DOCS_DIR="apps/docs/content"
ARCHIVE_DIR="$DOCS_DIR/archive"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running from project root
check_project_root() {
    if [ ! -d "$DOCS_DIR" ] || [ ! -d "apps/docs" ]; then
        print_error "Must run from project root directory"
        exit 1
    fi
}

# List draft content
list_drafts() {
    print_header "Draft Documentation"

    if [ ! -d "$DRAFTS_DIR" ]; then
        mkdir -p "$DRAFTS_DIR"
        print_warning "Drafts directory created"
    fi

    local draft_count=$(find "$DRAFTS_DIR" -name "*.md" -o -name "*.mdx" 2>/dev/null | wc -l)

    if [ "$draft_count" -eq 0 ]; then
        echo "No drafts found"
    else
        echo "Found $draft_count draft(s):"
        find "$DRAFTS_DIR" -name "*.md" -o -name "*.mdx" -exec basename {} \; 2>/dev/null | sed 's/^/  - /'
    fi
}

# Validate content before promotion
validate_content() {
    local file=$1
    local errors=0

    echo "Validating: $(basename $file)"

    # Check for sensitive information
    if grep -qE "(api[_-]?key|secret|password|token|private[_-]?key)" "$file" 2>/dev/null; then
        print_warning "  Potential sensitive information detected"
        ((errors++))
    fi

    # Check for internal URLs
    if grep -qE "(localhost|127\.0\.0\.1|internal\.|staging\.)" "$file" 2>/dev/null; then
        print_warning "  Internal URLs detected"
        ((errors++))
    fi

    # Check for broken internal links
    local broken_links=$(grep -oE '\[.*\]\((/docs/[^)]+)\)' "$file" 2>/dev/null | grep -oE '/docs/[^)]+' | while read link; do
        if [ ! -f ".$link" ] && [ ! -f ".$link.md" ] && [ ! -f ".$link.mdx" ]; then
            echo "$link"
        fi
    done)

    if [ ! -z "$broken_links" ]; then
        print_warning "  Broken internal links detected:"
        echo "$broken_links" | sed 's/^/    - /'
        ((errors++))
    fi

    # Check for TODO/FIXME comments
    if grep -qE "(TODO|FIXME|XXX|HACK)" "$file" 2>/dev/null; then
        print_warning "  Unresolved TODO/FIXME comments found"
        ((errors++))
    fi

    if [ $errors -eq 0 ]; then
        print_success "  Validation passed"
        return 0
    else
        print_error "  Validation found $errors issue(s)"
        return 1
    fi
}

# Promote draft to public documentation
promote_draft() {
    local draft_file=$1
    local target_dir=$2

    if [ ! -f "$draft_file" ]; then
        print_error "Draft file not found: $draft_file"
        return 1
    fi

    # Validate before promotion
    if ! validate_content "$draft_file"; then
        read -p "Validation failed. Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Promotion cancelled"
            return 1
        fi
    fi

    # Determine target location
    local filename=$(basename "$draft_file")
    local target_path="$PUBLIC_DOCS_DIR/$target_dir/$filename"

    # Create target directory if needed
    mkdir -p "$(dirname "$target_path")"

    # Move file
    mv "$draft_file" "$target_path"
    print_success "Promoted to: $target_path"

    # Git add the new file
    git add "$target_path" 2>/dev/null || true

    return 0
}

# Check for duplicate content
check_duplicates() {
    print_header "Checking for Duplicate Content"

    # Find potential duplicates by filename
    local duplicates=$(find "$DOCS_DIR" "apps/docs" -name "*.md" -o -name "*.mdx" 2>/dev/null | \
        xargs -I {} basename {} | \
        sort | uniq -d)

    if [ -z "$duplicates" ]; then
        print_success "No duplicate filenames found"
    else
        print_warning "Potential duplicate files found:"
        echo "$duplicates" | while read dup; do
            echo "  Duplicate: $dup"
            find "$DOCS_DIR" "apps/docs" -name "$dup" 2>/dev/null | sed 's/^/    - /'
        done
    fi

    # Check for similar content using checksums
    echo ""
    echo "Checking for identical content..."
    local identical_files=$(find "$DOCS_DIR" "apps/docs" -name "*.md" -o -name "*.mdx" 2>/dev/null | \
        xargs -I {} md5sum {} 2>/dev/null | \
        sort | \
        awk '{if (last == $1) {print $2}; last = $1}')

    if [ -z "$identical_files" ]; then
        print_success "No files with identical content found"
    else
        print_warning "Files with identical content:"
        echo "$identical_files" | sed 's/^/  - /'
    fi
}

# Archive old documentation
archive_content() {
    local file=$1
    local archive_reason=$2

    if [ ! -f "$file" ]; then
        print_error "File not found: $file"
        return 1
    fi

    local timestamp=$(date +%Y%m%d)
    local filename=$(basename "$file")
    local archive_path="$ARCHIVE_DIR/${timestamp}_${archive_reason}/"

    mkdir -p "$archive_path"
    mv "$file" "$archive_path/$filename"

    print_success "Archived to: $archive_path/$filename"
    return 0
}

# Health check for documentation
health_check() {
    print_header "Documentation Health Check"

    local issues=0

    # Check for orphaned quickstart directory
    if [ -d "$DOCS_DIR/quickstart" ]; then
        print_error "Orphaned quickstart directory exists"
        ((issues++))
    fi

    # Check drafts directory
    local draft_count=$(find "$DRAFTS_DIR" -name "*.md" -o -name "*.mdx" 2>/dev/null | wc -l)
    if [ "$draft_count" -gt 10 ]; then
        print_warning "$draft_count drafts pending (consider reviewing)"
        ((issues++))
    fi

    # Check for broken cross-references
    echo "Checking cross-references..."
    local broken_refs=$(grep -r '\[.*\]\((\.\.\/[^)]+)\)' "$DOCS_DIR" --include="*.md" 2>/dev/null | \
        while IFS=: read -r file ref; do
            ref_path=$(echo "$ref" | grep -oE '\(\.\./[^)]+\)' | tr -d '()' | head -1)
            abs_path=$(cd "$(dirname "$file")" && realpath "$ref_path" 2>/dev/null)
            if [ ! -f "$abs_path" ]; then
                echo "$file: $ref_path"
            fi
        done)

    if [ ! -z "$broken_refs" ]; then
        print_warning "Broken cross-references found:"
        echo "$broken_refs" | head -5 | sed 's/^/  - /'
        ((issues++))
    fi

    # Summary
    echo ""
    if [ $issues -eq 0 ]; then
        print_success "Documentation health check passed!"
    else
        print_warning "Found $issues issue(s) to review"
    fi

    return $issues
}

# Interactive menu
show_menu() {
    print_header "Documentation Pipeline Manager"
    echo "1) List draft content"
    echo "2) Promote draft to public"
    echo "3) Check for duplicates"
    echo "4) Run health check"
    echo "5) Archive old content"
    echo "6) Validate specific file"
    echo "7) Exit"
    echo ""
    read -p "Select option: " choice

    case $choice in
        1)
            list_drafts
            ;;
        2)
            list_drafts
            echo ""
            read -p "Enter draft filename to promote: " draft_name
            read -p "Enter target directory (e.g., guides, api, sdks): " target_dir
            promote_draft "$DRAFTS_DIR/$draft_name" "$target_dir"
            ;;
        3)
            check_duplicates
            ;;
        4)
            health_check
            ;;
        5)
            read -p "Enter file path to archive: " file_path
            read -p "Enter reason (deprecated/outdated/replaced): " reason
            archive_content "$file_path" "$reason"
            ;;
        6)
            read -p "Enter file path to validate: " file_path
            validate_content "$file_path"
            ;;
        7)
            exit 0
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

# Main execution
main() {
    check_project_root

    # Parse command line arguments
    case "${1:-}" in
        list|ls)
            list_drafts
            ;;
        promote)
            if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
                print_error "Usage: $0 promote <draft-file> <target-dir>"
                exit 1
            fi
            promote_draft "$2" "$3"
            ;;
        check|duplicates)
            check_duplicates
            ;;
        health)
            health_check
            ;;
        validate)
            if [ -z "${2:-}" ]; then
                print_error "Usage: $0 validate <file>"
                exit 1
            fi
            validate_content "$2"
            ;;
        archive)
            if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
                print_error "Usage: $0 archive <file> <reason>"
                exit 1
            fi
            archive_content "$2" "$3"
            ;;
        *)
            show_menu
            ;;
    esac
}

main "$@"