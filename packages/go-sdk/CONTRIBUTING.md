# Contributing to Janua Go SDK

## Development Setup

### Prerequisites
- Go 1.21 or higher
- Make (optional, but recommended)
- Git

### Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/madfam-io/janua.git
   cd janua/packages/go-sdk
   ```

2. **Install dependencies**:
   ```bash
   go mod download
   ```

3. **Install development tools** (optional):
   ```bash
   make install-tools
   ```

## Building the SDK

### Using Make (Recommended)

```bash
# Build the SDK
make build

# Run tests
make test

# Run tests with coverage
make test-coverage

# Run all checks (format, vet, lint, test)
make check

# Run CI pipeline
make ci
```

### Using build.sh

```bash
# Basic build
./build.sh

# Build with coverage report
./build.sh --coverage
```

### Manual Build

```bash
# Tidy dependencies
go mod tidy

# Download dependencies
go mod download

# Verify dependencies
go mod verify

# Format code
go fmt ./...

# Run go vet
go vet ./...

# Build all packages
go build -v ./...

# Run tests
go test -v -race ./...

# Run linter (if golangci-lint installed)
golangci-lint run ./...
```

## Project Structure

```
go-sdk/
├── janua/           # Main SDK package
│   ├── client.go     # Main client implementation
│   ├── auth.go       # Authentication methods
│   ├── users.go      # User management
│   └── organizations.go  # Organization management
├── models/           # Data models and types
├── auth/             # Authentication helpers
├── examples/         # Usage examples
├── go.mod            # Go modules file
├── go.sum            # Go modules checksums
├── Makefile          # Build automation
├── build.sh          # Build script
├── .golangci.yml     # Linter configuration
└── README.md         # Documentation
```

## Testing

### Run All Tests
```bash
make test
```

### Run Tests with Coverage
```bash
make test-coverage
```

### Run Tests for Specific Package
```bash
go test -v ./janua
```

### Run Tests with Race Detector
```bash
go test -race ./...
```

## Code Quality

### Formatting
The project uses standard Go formatting:
```bash
make fmt
# or
go fmt ./...
```

### Linting
We use golangci-lint for comprehensive code analysis:
```bash
make lint
# or
golangci-lint run ./...
```

### Vetting
```bash
make vet
# or
go vet ./...
```

## Dependency Management

### Adding Dependencies
```bash
go get github.com/example/package@version
go mod tidy
```

### Updating Dependencies
```bash
go get -u ./...
go mod tidy
```

### Verifying Dependencies
```bash
go mod verify
```

## Release Process

1. **Update version** in go.mod and documentation
2. **Run full CI pipeline**:
   ```bash
   make ci
   ```
3. **Create git tag**:
   ```bash
   make tag VERSION=v1.0.0
   ```
4. **Push to repository** (triggers GitHub Actions)

## Common Tasks

### Running Examples
```bash
make run-example EXAMPLE=basic
# or
go run examples/basic/main.go
```

### Cleaning Build Artifacts
```bash
make clean
```

### View All Available Commands
```bash
make help
```

## Troubleshooting

### Dependencies Not Found
```bash
go mod download
go mod verify
```

### Build Failures
```bash
go clean
go mod tidy
make build
```

### Test Failures
```bash
# Run tests with verbose output
go test -v ./...

# Run specific test
go test -v -run TestSpecificFunction ./janua
```

## Code Style Guidelines

- Follow standard Go conventions
- Write tests for all new functionality
- Document exported functions and types
- Keep functions focused and small
- Use meaningful variable names
- Handle errors explicitly

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make ci` to verify all checks pass
5. Commit with descriptive messages
6. Push to your fork
7. Create a pull request

## License

AGPL-3.0 License - see LICENSE file for details
