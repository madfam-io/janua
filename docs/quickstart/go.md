# Go SDK Quickstart

Get started with Plinto authentication in your Go application with idiomatic Go patterns.

## Installation

```bash
go get github.com/plinto/go-sdk
```

## Basic Setup

```go
package main

import (
    "context"
    "log"
    
    plinto "github.com/plinto/go-sdk/plinto"
)

func main() {
    // Initialize client
    client := plinto.NewClient(plinto.Config{
        BaseURL: "https://api.plinto.dev",
        APIKey:  "YOUR_API_KEY",
        TenantID: "YOUR_TENANT_ID",
    })
    
    ctx := context.Background()
    
    // Use the client
    user, err := client.Users.GetCurrentUser(ctx)
    if err != nil {
        log.Fatal(err)
    }
    
    log.Printf("Logged in as: %s", user.Email)
}
```

## Quick Examples

### Sign Up
```go
ctx := context.Background()

response, err := client.Auth.SignUp(ctx, &plinto.SignUpRequest{
    Email:     "user@example.com",
    Password:  "SecurePassword123!",
    FirstName: "John",
    LastName:  "Doe",
})

if err != nil {
    if apiErr, ok := err.(*plinto.APIError); ok {
        log.Printf("API Error [%s]: %s", apiErr.Code, apiErr.Message)
    } else {
        log.Fatal(err)
    }
}

log.Printf("Welcome, %s!", response.User.FirstName)
```

### Sign In
```go
response, err := client.Auth.SignIn(ctx, &plinto.SignInRequest{
    Email:    "user@example.com",
    Password: "SecurePassword123!",
})

if err != nil {
    log.Fatal(err)
}

log.Printf("Signed in: %s", response.User.Email)
// Tokens are automatically stored
```

### Sign Out
```go
err := client.Auth.SignOut(ctx)
if err != nil {
    log.Fatal(err)
}

log.Println("Signed out successfully")
```

## Error Handling

```go
import "errors"

response, err := client.Auth.SignIn(ctx, req)
if err != nil {
    var apiErr *plinto.APIError
    if errors.As(err, &apiErr) {
        switch apiErr.Code {
        case "INVALID_CREDENTIALS":
            log.Println("Invalid email or password")
        case "ACCOUNT_LOCKED":
            log.Println("Account is locked")
        case "MFA_REQUIRED":
            log.Println("MFA verification required")
        default:
            log.Printf("API Error: %s", apiErr.Message)
        }
    } else {
        // Network or other errors
        log.Printf("Error: %v", err)
    }
}
```

## Context and Timeouts

```go
// With timeout
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

user, err := client.Users.GetCurrentUser(ctx)
if err != nil {
    if errors.Is(err, context.DeadlineExceeded) {
        log.Println("Request timed out")
    }
}

// With cancellation
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

// Cancel after some condition
go func() {
    time.Sleep(5 * time.Second)
    cancel()
}()

user, err := client.Users.GetCurrentUser(ctx)
```

## Multi-Factor Authentication

### Enable MFA
```go
setup, err := client.Auth.EnableMFA(ctx, &plinto.EnableMFARequest{
    Method: "totp",
})

if err != nil {
    log.Fatal(err)
}

log.Printf("QR Code: %s", setup.QRCode)
log.Printf("Recovery Codes: %v", setup.RecoveryCodes)
```

### Verify MFA
```go
err := client.Auth.VerifyMFA(ctx, &plinto.VerifyMFARequest{
    Code:        "123456",
    ChallengeID: challengeID,
})

if err != nil {
    log.Fatal(err)
}

log.Println("MFA verified successfully")
```

## Session Management

### List Sessions
```go
sessions, err := client.Sessions.List(ctx, &plinto.ListOptions{
    Page:    1,
    PerPage: 20,
})

if err != nil {
    log.Fatal(err)
}

for _, session := range sessions.Items {
    log.Printf("Device: %s, Location: %s", session.Device, session.Location)
}
```

### Revoke Session
```go
err := client.Sessions.Revoke(ctx, sessionID)
if err != nil {
    log.Fatal(err)
}
```

## Organization Management

### List Organizations
```go
orgs, err := client.Organizations.List(ctx, &plinto.ListOptions{
    Page: 1,
    PerPage: 10,
})

if err != nil {
    log.Fatal(err)
}

for _, org := range orgs.Items {
    log.Printf("%s - Role: %s", org.Name, org.Role)
}
```

### Create Organization
```go
org, err := client.Organizations.Create(ctx, &plinto.CreateOrganizationRequest{
    Name:        "My Company",
    Description: "A great place to work",
    Metadata: map[string]interface{}{
        "industry": "technology",
        "size":     "50-100",
    },
})

if err != nil {
    log.Fatal(err)
}

log.Printf("Created organization: %s", org.ID)
```

## OAuth/Social Login

```go
// Get authorization URL
authURL, err := client.Auth.GetOAuthURL(ctx, "google")
if err != nil {
    log.Fatal(err)
}

log.Printf("Redirect user to: %s", authURL)

// Handle callback (in your HTTP handler)
func handleOAuthCallback(w http.ResponseWriter, r *http.Request) {
    code := r.URL.Query().Get("code")
    state := r.URL.Query().Get("state")
    
    response, err := client.Auth.HandleOAuthCallback(r.Context(), &plinto.OAuthCallbackRequest{
        Code:  code,
        State: state,
    })
    
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    // User is now authenticated
    log.Printf("OAuth login successful: %s", response.User.Email)
}
```

## Middleware

### HTTP Middleware
```go
func PlintoAuthMiddleware(client *plinto.Client) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Extract token from header
            authHeader := r.Header.Get("Authorization")
            if authHeader == "" {
                http.Error(w, "Unauthorized", http.StatusUnauthorized)
                return
            }
            
            token := strings.TrimPrefix(authHeader, "Bearer ")
            
            // Verify token and get user
            user, err := client.Users.GetCurrentUser(r.Context())
            if err != nil {
                http.Error(w, "Invalid token", http.StatusUnauthorized)
                return
            }
            
            // Add user to context
            ctx := context.WithValue(r.Context(), "user", user)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

// Usage
mux := http.NewServeMux()
mux.Handle("/protected", PlintoAuthMiddleware(client)(protectedHandler))
```

### Gin Middleware
```go
import "github.com/gin-gonic/gin"

func PlintoAuth(client *plinto.Client) gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.JSON(401, gin.H{"error": "Unauthorized"})
            c.Abort()
            return
        }
        
        user, err := client.Users.GetCurrentUser(c.Request.Context())
        if err != nil {
            c.JSON(401, gin.H{"error": "Invalid token"})
            c.Abort()
            return
        }
        
        c.Set("user", user)
        c.Next()
    }
}

// Usage
router := gin.Default()
protected := router.Group("/api")
protected.Use(PlintoAuth(client))
```

### Echo Middleware
```go
import "github.com/labstack/echo/v4"

func PlintoAuthMiddleware(client *plinto.Client) echo.MiddlewareFunc {
    return func(next echo.HandlerFunc) echo.HandlerFunc {
        return func(c echo.Context) error {
            token := c.Request().Header.Get("Authorization")
            if token == "" {
                return c.JSON(401, map[string]string{"error": "Unauthorized"})
            }
            
            user, err := client.Users.GetCurrentUser(c.Request().Context())
            if err != nil {
                return c.JSON(401, map[string]string{"error": "Invalid token"})
            }
            
            c.Set("user", user)
            return next(c)
        }
    }
}

// Usage
e := echo.New()
e.Use(PlintoAuthMiddleware(client))
```

## Advanced Configuration

### Custom HTTP Client
```go
import (
    "net/http"
    "time"
)

httpClient := &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

client := plinto.NewClient(plinto.Config{
    BaseURL:    "https://api.plinto.dev",
    APIKey:     "YOUR_API_KEY",
    TenantID:   "YOUR_TENANT_ID",
    HTTPClient: httpClient,
})
```

### Retry Configuration
```go
client := plinto.NewClient(plinto.Config{
    BaseURL:  "https://api.plinto.dev",
    APIKey:   "YOUR_API_KEY",
    TenantID: "YOUR_TENANT_ID",
    RetryConfig: &plinto.RetryConfig{
        MaxRetries:    3,
        RetryWaitMin:  1 * time.Second,
        RetryWaitMax:  30 * time.Second,
        RetryStatuses: []int{500, 502, 503, 504},
    },
})
```

## Testing

### Mock Client
```go
import (
    "testing"
    "github.com/stretchr/testify/mock"
)

type MockClient struct {
    mock.Mock
}

func (m *MockClient) SignIn(ctx context.Context, req *plinto.SignInRequest) (*plinto.AuthResponse, error) {
    args := m.Called(ctx, req)
    return args.Get(0).(*plinto.AuthResponse), args.Error(1)
}

func TestSignIn(t *testing.T) {
    mockClient := new(MockClient)
    
    expectedResponse := &plinto.AuthResponse{
        User: &plinto.User{
            Email: "test@example.com",
        },
    }
    
    mockClient.On("SignIn", mock.Anything, mock.Anything).Return(expectedResponse, nil)
    
    response, err := mockClient.SignIn(context.Background(), &plinto.SignInRequest{
        Email:    "test@example.com",
        Password: "password",
    })
    
    assert.NoError(t, err)
    assert.Equal(t, "test@example.com", response.User.Email)
    mockClient.AssertExpectations(t)
}
```

### Integration Testing
```go
func TestIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test")
    }
    
    client := plinto.NewClient(plinto.Config{
        BaseURL:  os.Getenv("TEST_PLINTO_URL"),
        APIKey:   os.Getenv("TEST_API_KEY"),
        TenantID: os.Getenv("TEST_TENANT_ID"),
    })
    
    ctx := context.Background()
    
    // Create test user
    testEmail := fmt.Sprintf("test-%d@example.com", time.Now().Unix())
    
    response, err := client.Auth.SignUp(ctx, &plinto.SignUpRequest{
        Email:     testEmail,
        Password:  "TestPassword123!",
        FirstName: "Test",
        LastName:  "User",
    })
    
    require.NoError(t, err)
    assert.Equal(t, testEmail, response.User.Email)
    
    // Clean up
    defer func() {
        err := client.Users.Delete(ctx, response.User.ID)
        assert.NoError(t, err)
    }()
}
```

## Best Practices

### 1. Use Context Everywhere
```go
// Good
func getUser(ctx context.Context, client *plinto.Client, userID string) (*plinto.User, error) {
    return client.Users.Get(ctx, userID)
}

// Bad - no context
func getUser(client *plinto.Client, userID string) (*plinto.User, error) {
    return client.Users.Get(context.Background(), userID)
}
```

### 2. Proper Error Handling
```go
func handleAuth(client *plinto.Client) error {
    response, err := client.Auth.SignIn(ctx, req)
    if err != nil {
        // Type assert to get more details
        if apiErr, ok := err.(*plinto.APIError); ok {
            log.Printf("API Error [%s]: %s", apiErr.Code, apiErr.Message)
            
            // Handle specific errors
            switch apiErr.Code {
            case "RATE_LIMITED":
                time.Sleep(time.Duration(apiErr.RetryAfter) * time.Second)
                return handleAuth(client) // Retry
            default:
                return fmt.Errorf("auth failed: %w", err)
            }
        }
        return fmt.Errorf("unexpected error: %w", err)
    }
    return nil
}
```

### 3. Connection Pooling
```go
// Singleton pattern for client
var (
    clientInstance *plinto.Client
    clientOnce     sync.Once
)

func GetClient() *plinto.Client {
    clientOnce.Do(func() {
        clientInstance = plinto.NewClient(plinto.Config{
            BaseURL:  os.Getenv("PLINTO_URL"),
            APIKey:   os.Getenv("PLINTO_API_KEY"),
            TenantID: os.Getenv("PLINTO_TENANT_ID"),
        })
    })
    return clientInstance
}
```

## Logging

```go
import (
    "log/slog"
)

// Custom logger
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelDebug,
}))

client := plinto.NewClient(plinto.Config{
    BaseURL:  "https://api.plinto.dev",
    APIKey:   "YOUR_API_KEY",
    TenantID: "YOUR_TENANT_ID",
    Logger:   logger,
})
```

## Next Steps

- [Full Go API Reference](/docs/api/go)
- [HTTP Middleware Guide](/docs/guides/go-middleware)
- [Testing Guide](/docs/guides/go-testing)
- [Examples Repository](https://github.com/plinto/go-examples)

## Support

- 📖 [Documentation](https://docs.plinto.dev)
- 🐹 [Go Examples](https://github.com/plinto/go-examples)
- 💬 [Community Forum](https://community.plinto.dev)
- 📧 [Support](mailto:support@plinto.dev)