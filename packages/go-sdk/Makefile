# Makefile for Plinto Go SDK

.PHONY: help build test lint fmt vet tidy clean install-tools

# Default target
.DEFAULT_GOAL := help

# Variables
GOCMD=go
GOBUILD=$(GOCMD) build
GOTEST=$(GOCMD) test
GOCLEAN=$(GOCMD) clean
GOGET=$(GOCMD) get
GOMOD=$(GOCMD) mod
GOFMT=$(GOCMD) fmt
GOVET=$(GOCMD) vet
GOLINT=golangci-lint

# Build targets
help: ## Display this help message
	@echo "Plinto Go SDK - Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the SDK
	@echo "Building Go SDK..."
	$(GOBUILD) -v ./...
	@echo "✅ Build complete"

test: ## Run tests
	@echo "Running tests..."
	$(GOTEST) -v -race -coverprofile=coverage.out ./...
	@echo "✅ Tests complete"

test-coverage: test ## Run tests with coverage report
	@echo "Generating coverage report..."
	$(GOCMD) tool cover -html=coverage.out -o coverage.html
	@echo "✅ Coverage report: coverage.html"

lint: ## Run linter
	@echo "Running linter..."
	@if command -v $(GOLINT) > /dev/null; then \
		$(GOLINT) run ./...; \
	else \
		echo "⚠️  golangci-lint not installed. Run 'make install-tools'"; \
	fi

fmt: ## Format code
	@echo "Formatting code..."
	$(GOFMT) ./...
	@echo "✅ Code formatted"

vet: ## Run go vet
	@echo "Running go vet..."
	$(GOVET) ./...
	@echo "✅ Vet complete"

tidy: ## Tidy dependencies
	@echo "Tidying dependencies..."
	$(GOMOD) tidy
	@echo "✅ Dependencies tidied"

download: ## Download dependencies
	@echo "Downloading dependencies..."
	$(GOMOD) download
	@echo "✅ Dependencies downloaded"

verify: ## Verify dependencies
	@echo "Verifying dependencies..."
	$(GOMOD) verify
	@echo "✅ Dependencies verified"

clean: ## Clean build artifacts
	@echo "Cleaning..."
	$(GOCLEAN)
	rm -f coverage.out coverage.html
	@echo "✅ Clean complete"

install-tools: ## Install development tools
	@echo "Installing development tools..."
	@echo "Installing golangci-lint..."
	@if ! command -v golangci-lint > /dev/null; then \
		curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin v1.55.2; \
	fi
	@echo "✅ Tools installed"

check: fmt vet lint test ## Run all checks (fmt, vet, lint, test)

ci: tidy check ## CI pipeline (tidy, format, vet, lint, test)

# Versioning and release
tag: ## Create a new git tag (usage: make tag VERSION=v1.0.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION is required. Usage: make tag VERSION=v1.0.0"; \
		exit 1; \
	fi
	@echo "Creating tag $(VERSION)..."
	git tag -a $(VERSION) -m "Release $(VERSION)"
	git push origin $(VERSION)
	@echo "✅ Tag $(VERSION) created and pushed"

# Examples
run-example: ## Run an example (usage: make run-example EXAMPLE=basic)
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "❌ EXAMPLE is required. Usage: make run-example EXAMPLE=basic"; \
		exit 1; \
	fi
	@echo "Running example: $(EXAMPLE)"
	$(GOCMD) run examples/$(EXAMPLE)/main.go
