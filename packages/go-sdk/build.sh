#!/bin/bash
# Build script for Plinto Go SDK

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔨 Building Plinto Go SDK${NC}"

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo -e "${RED}❌ Go is not installed${NC}"
    exit 1
fi

# Print Go version
GO_VERSION=$(go version)
echo -e "${GREEN}✓ Go installed: ${GO_VERSION}${NC}"

# Tidy dependencies
echo -e "${YELLOW}📦 Tidying dependencies...${NC}"
go mod tidy
echo -e "${GREEN}✓ Dependencies tidied${NC}"

# Download dependencies
echo -e "${YELLOW}⬇️  Downloading dependencies...${NC}"
go mod download
echo -e "${GREEN}✓ Dependencies downloaded${NC}"

# Verify dependencies
echo -e "${YELLOW}🔍 Verifying dependencies...${NC}"
go mod verify
echo -e "${GREEN}✓ Dependencies verified${NC}"

# Format code
echo -e "${YELLOW}📝 Formatting code...${NC}"
go fmt ./...
echo -e "${GREEN}✓ Code formatted${NC}"

# Run go vet
echo -e "${YELLOW}🔎 Running go vet...${NC}"
go vet ./...
echo -e "${GREEN}✓ Vet passed${NC}"

# Build all packages
echo -e "${YELLOW}🏗️  Building packages...${NC}"
go build -v ./...
echo -e "${GREEN}✓ Build successful${NC}"

# Run tests
echo -e "${YELLOW}🧪 Running tests...${NC}"
go test -v -race -coverprofile=coverage.out ./...
echo -e "${GREEN}✓ Tests passed${NC}"

# Generate coverage report
if [ "$1" = "--coverage" ]; then
    echo -e "${YELLOW}📊 Generating coverage report...${NC}"
    go tool cover -html=coverage.out -o coverage.html
    echo -e "${GREEN}✓ Coverage report: coverage.html${NC}"
fi

# Run linter if available
if command -v golangci-lint &> /dev/null; then
    echo -e "${YELLOW}🔍 Running linter...${NC}"
    golangci-lint run ./...
    echo -e "${GREEN}✓ Lint passed${NC}"
else
    echo -e "${YELLOW}⚠️  golangci-lint not installed, skipping linter${NC}"
fi

echo -e "${GREEN}✅ Build complete!${NC}"
