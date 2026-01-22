module github.com/madfam-org/janua/packages/go-sdk

go 1.23.0

require (
	github.com/golang-jwt/jwt/v5 v5.2.2 // CVE-2025-30204 fix
	github.com/google/uuid v1.6.0
	github.com/gorilla/websocket v1.5.3
	golang.org/x/oauth2 v0.27.0 // CVE-2025-22868 fix
)

require (
	golang.org/x/net v0.38.0 // indirect - CVE-2025-22870, CVE-2025-22872 fix
	google.golang.org/protobuf v1.36.0 // indirect - CVE-2024-24786 fix
)
