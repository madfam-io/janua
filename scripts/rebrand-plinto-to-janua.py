#!/usr/bin/env python3
"""
Comprehensive Janua → Janua rebranding script
Handles case-sensitive replacements across the entire codebase
"""

import re
from pathlib import Path
from typing import List, Tuple

# Directories to exclude
EXCLUDE_DIRS = {
    'node_modules', '.next', 'dist', 'dist-cjs', '.git',
    'build', '__pycache__', '.pytest_cache', 'coverage',
    '.turbo', '.cache', 'out'
}

# File extensions to process
INCLUDE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.py', '.go', '.md', '.json', '.yaml', '.yml',
    '.toml', '.sql', '.sh', '.conf', '.txt', '.ejs',
    '.html', '.css', '.graphql', '.tpl', '.Makefile',
    '.ini', '.env'
}

# Special filenames to include
SPECIAL_FILES = {
    '.env.example', 'Makefile', 'Dockerfile', 'docker-compose.yml',
    'requirements.txt', 'setup.py', 'pyproject.toml'
}

def should_process(file_path: Path) -> bool:
    """Check if file should be processed"""
    # Check if any excluded directory is in the path
    parts = file_path.parts
    if any(excluded in parts for excluded in EXCLUDE_DIRS):
        return False

    # Check extension or special filename
    if file_path.suffix in INCLUDE_EXTENSIONS or file_path.name in SPECIAL_FILES:
        return True

    return False

def rebrand_file(file_path: Path) -> Tuple[bool, int]:
    """
    Apply rebranding to a single file
    Returns: (was_modified, replacement_count)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Check if file contains any variant
        if not re.search(r'Janua|janua|JANUA', content):
            return False, 0

        # Count replacements for reporting
        count_upper = len(re.findall(r'JANUA', content))
        count_title = len(re.findall(r'Janua', content))
        count_lower = len(re.findall(r'janua', content))
        total_replacements = count_upper + count_title + count_lower

        # Apply replacements (order matters for correct casing)
        new_content = content
        new_content = re.sub(r'JANUA', 'JANUA', new_content)
        new_content = re.sub(r'Janua', 'Janua', new_content)
        new_content = re.sub(r'janua', 'janua', new_content)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True, total_replacements

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False, 0

def main():
    root_dir = Path.cwd()
    modified_count = 0
    total_replacements = 0
    modified_files: List[str] = []

    print("🔄 Starting comprehensive Janua → Janua rebranding...")
    print(f"📁 Root directory: {root_dir}")
    print()

    for file_path in root_dir.rglob('*'):
        if file_path.is_file() and should_process(file_path):
            was_modified, replacements = rebrand_file(file_path)
            if was_modified:
                modified_count += 1
                total_replacements += replacements
                rel_path = str(file_path.relative_to(root_dir))
                modified_files.append(rel_path)
                print(f"  ✓ {rel_path} ({replacements} replacements)")

    print()
    print("=" * 70)
    print("✅ Rebranding complete!")
    print(f"📊 Total files modified: {modified_count}")
    print(f"🔄 Total replacements: {total_replacements}")
    print("=" * 70)

    # Verification check
    print()
    print("🔍 Running verification check...")
    remaining_count = 0
    for file_path in root_dir.rglob('*'):
        if file_path.is_file() and should_process(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if re.search(r'Janua|janua|JANUA', f.read()):
                        remaining_count += 1
                        print(f"  ⚠️  Still contains 'Janua': {file_path.relative_to(root_dir)}")
            except Exception:
                pass

    if remaining_count == 0:
        print("✅ Verification passed: No 'Janua' references remaining!")
    else:
        print(f"⚠️  Warning: {remaining_count} files still contain 'Janua' references")

    print()
    print("📝 Summary of modified files written to: rebrand-summary.txt")

    # Write summary
    with open(root_dir / 'rebrand-summary.txt', 'w') as f:
        f.write(f"Janua → Janua Rebranding Summary\n")
        f.write(f"=" * 70 + "\n\n")
        f.write(f"Total files modified: {modified_count}\n")
        f.write(f"Total replacements: {total_replacements}\n\n")
        f.write(f"Modified files:\n")
        for file in sorted(modified_files):
            f.write(f"  - {file}\n")

if __name__ == '__main__':
    main()
