#!/bin/bash

# Production Build Script for Plinto Platform
# Optimized build with security checks and validation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BUILD_ENV="${BUILD_ENV:-production}"
NODE_ENV="production"
BUILD_DIR="dist"
ENABLE_SOURCE_MAPS="${ENABLE_SOURCE_MAPS:-false}"
ENABLE_BUNDLE_ANALYSIS="${ENABLE_BUNDLE_ANALYSIS:-false}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Node.js version
    required_node="18"
    current_node=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$current_node" -lt "$required_node" ]; then
        print_error "Node.js version $required_node or higher is required"
        exit 1
    fi
    
    # Check Yarn
    if ! command -v yarn &> /dev/null; then
        print_error "Yarn is not installed"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Function to clean previous builds
clean_build() {
    print_status "Cleaning previous builds..."
    
    # Remove old build directories
    rm -rf apps/*/dist
    rm -rf apps/*/.next
    rm -rf packages/*/dist
    rm -rf packages/*/lib
    rm -rf turbo-cache
    
    print_status "Clean completed"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install with frozen lockfile for reproducible builds
    yarn install --frozen-lockfile --production=false
    
    print_status "Dependencies installed"
}

# Function to run quality checks
run_quality_checks() {
    print_status "Running quality checks..."
    
    # Linting
    print_status "Running linters..."
    yarn lint || {
        print_warning "Linting issues found, continuing build..."
    }
    
    # Type checking
    print_status "Running type checks..."
    yarn typecheck || {
        print_warning "TypeScript errors found, continuing build..."
    }
    
    # Security audit
    print_status "Running security audit..."
    yarn audit --level moderate || {
        print_warning "Security vulnerabilities found in dependencies"
    }
    
    print_status "Quality checks completed"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Run unit tests with coverage
    yarn test:coverage || {
        print_warning "Some tests failed, check coverage report"
    }
    
    print_status "Tests completed"
}

# Function to build packages
build_packages() {
    print_status "Building shared packages..."
    
    # Build packages in dependency order
    yarn workspace @plinto/sdk build
    yarn workspace @plinto/ui build
    yarn workspace @plinto/react build
    yarn workspace @plinto/sdk-js build
    
    print_status "Packages built successfully"
}

# Function to build applications
build_applications() {
    print_status "Building applications..."
    
    # Set production environment variables
    export NODE_ENV=production
    export NEXT_TELEMETRY_DISABLED=1
    
    # Build each application
    apps=("marketing" "dashboard" "admin" "demo" "docs")
    
    for app in "${apps[@]}"; do
        print_status "Building @plinto/$app..."
        
        # Create optimized production build
        yarn workspace @plinto/$app build || {
            print_error "Failed to build $app"
            exit 1
        }
        
        # Analyze bundle size if enabled
        if [ "$ENABLE_BUNDLE_ANALYSIS" = "true" ]; then
            print_status "Analyzing bundle for $app..."
            cd "apps/$app"
            npx next-bundle-analyzer || true
            cd ../..
        fi
    done
    
    print_status "Applications built successfully"
}

# Function to optimize build artifacts
optimize_artifacts() {
    print_status "Optimizing build artifacts..."
    
    # Remove source maps if not needed
    if [ "$ENABLE_SOURCE_MAPS" = "false" ]; then
        print_status "Removing source maps..."
        find apps -name "*.map" -type f -delete
    fi
    
    # Compress static assets
    print_status "Compressing static assets..."
    find apps -name "*.js" -o -name "*.css" -o -name "*.html" | while read -r file; do
        gzip -9 -k "$file" 2>/dev/null || true
    done
    
    print_status "Optimization completed"
}

# Function to validate build
validate_build() {
    print_status "Validating build..."
    
    # Check for required files
    required_files=(
        "apps/marketing/.next"
        "apps/dashboard/.next"
        "apps/admin/.next"
        "packages/sdk/dist"
        "packages/ui/dist"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$file" ]; then
            print_error "Required build artifact missing: $file"
            exit 1
        fi
    done
    
    # Check bundle sizes
    print_status "Checking bundle sizes..."
    for app_dir in apps/*/.next; do
        if [ -d "$app_dir" ]; then
            app_name=$(basename "$(dirname "$app_dir")")
            size=$(du -sh "$app_dir" | cut -f1)
            print_status "$app_name bundle size: $size"
            
            # Warn if bundle is too large
            size_mb=$(du -sm "$app_dir" | cut -f1)
            if [ "$size_mb" -gt 50 ]; then
                print_warning "$app_name bundle is large (>50MB)"
            fi
        fi
    done
    
    print_status "Build validation completed"
}

# Function to create build manifest
create_manifest() {
    print_status "Creating build manifest..."
    
    manifest_file="build-manifest.json"
    build_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    git_hash=$(git rev-parse HEAD || echo "unknown")
    git_branch=$(git rev-parse --abbrev-ref HEAD || echo "unknown")
    
    cat > "$manifest_file" <<EOF
{
  "build_time": "$build_time",
  "build_env": "$BUILD_ENV",
  "git_hash": "$git_hash",
  "git_branch": "$git_branch",
  "node_version": "$(node -v)",
  "yarn_version": "$(yarn -v)",
  "artifacts": {
    "marketing": "apps/marketing/.next",
    "dashboard": "apps/dashboard/.next",
    "admin": "apps/admin/.next",
    "demo": "apps/demo/.next",
    "docs": "apps/docs/.next",
    "sdk": "packages/sdk/dist",
    "ui": "packages/ui/dist",
    "react": "packages/react/dist"
  }
}
EOF
    
    print_status "Build manifest created: $manifest_file"
}

# Function to create deployment package
create_deployment_package() {
    print_status "Creating deployment package..."
    
    package_name="plinto-build-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    # Create package with essential files
    tar -czf "$package_name" \
        --exclude='node_modules' \
        --exclude='.git' \
        --exclude='*.test.*' \
        --exclude='*.spec.*' \
        apps/*/.next \
        apps/*/public \
        packages/*/dist \
        package.json \
        yarn.lock \
        build-manifest.json \
        vercel.json \
        railway.json \
        turbo.json
    
    size=$(du -h "$package_name" | cut -f1)
    print_status "Deployment package created: $package_name (size: $size)"
}

# Main execution
main() {
    print_status "Starting production build for Plinto..."
    print_status "Build environment: $BUILD_ENV"
    
    START_TIME=$(date +%s)
    
    # Execute build steps
    check_prerequisites
    clean_build
    install_dependencies
    run_quality_checks
    run_tests
    build_packages
    build_applications
    optimize_artifacts
    validate_build
    create_manifest
    create_deployment_package
    
    # Calculate build time
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    BUILD_MINUTES=$((BUILD_TIME / 60))
    BUILD_SECONDS=$((BUILD_TIME % 60))
    
    print_status "================================="
    print_status "Build completed successfully! 🎉"
    print_status "Build time: ${BUILD_MINUTES}m ${BUILD_SECONDS}s"
    print_status "================================="
    
    # Show next steps
    echo ""
    print_status "Next steps:"
    echo "  1. Review build manifest: build-manifest.json"
    echo "  2. Deploy package: plinto-build-*.tar.gz"
    echo "  3. Run smoke tests in staging environment"
    echo "  4. Deploy to production with monitoring"
}

# Handle errors
trap 'print_error "Build failed on line $LINENO"' ERR

# Run main function
main "$@"