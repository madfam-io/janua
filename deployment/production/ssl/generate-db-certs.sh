#!/bin/bash
# Generate SSL certificates for PostgreSQL database connections
# Run this script from the deployment/production/ssl directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_SSL_DIR="${SCRIPT_DIR}/db"

echo "=== Janua Database SSL Certificate Generator ==="
echo "Output directory: ${DB_SSL_DIR}"

# Create directory structure
mkdir -p "${DB_SSL_DIR}"

# Generate CA certificate (self-signed, 10 years validity)
echo ""
echo "1. Generating CA certificate..."
openssl req -new -x509 -days 3650 -nodes \
  -out "${DB_SSL_DIR}/ca.crt" \
  -keyout "${DB_SSL_DIR}/ca.key" \
  -subj "/CN=Janua-Internal-CA/O=MADFAM/OU=Infrastructure"

# Generate server certificate signing request
echo ""
echo "2. Generating server certificate..."
openssl req -new -nodes \
  -out "${DB_SSL_DIR}/server.csr" \
  -keyout "${DB_SSL_DIR}/server.key" \
  -subj "/CN=postgres/O=MADFAM/OU=Database"

# Sign server certificate with CA (1 year validity)
openssl x509 -req -in "${DB_SSL_DIR}/server.csr" \
  -CA "${DB_SSL_DIR}/ca.crt" \
  -CAkey "${DB_SSL_DIR}/ca.key" \
  -CAcreateserial -days 365 \
  -out "${DB_SSL_DIR}/server.crt"

# Set proper permissions (PostgreSQL requires specific permissions)
echo ""
echo "3. Setting permissions..."
chmod 600 "${DB_SSL_DIR}/server.key"
chmod 600 "${DB_SSL_DIR}/ca.key"
chmod 644 "${DB_SSL_DIR}/server.crt"
chmod 644 "${DB_SSL_DIR}/ca.crt"

# Clean up CSR (not needed after signing)
rm -f "${DB_SSL_DIR}/server.csr"

# Verify certificates
echo ""
echo "4. Verifying certificates..."
openssl verify -CAfile "${DB_SSL_DIR}/ca.crt" "${DB_SSL_DIR}/server.crt"

echo ""
echo "=== SSL Certificate Generation Complete ==="
echo ""
echo "Generated files:"
echo "  - ${DB_SSL_DIR}/ca.crt      (CA certificate - distribute to clients)"
echo "  - ${DB_SSL_DIR}/ca.key      (CA private key - keep secure!)"
echo "  - ${DB_SSL_DIR}/server.crt  (Server certificate)"
echo "  - ${DB_SSL_DIR}/server.key  (Server private key - keep secure!)"
echo ""
echo "Certificate validity:"
echo "  - CA: 10 years"
echo "  - Server: 1 year (regenerate annually)"
echo ""
echo "Next steps:"
echo "  1. Add ssl/db/*.crt and ssl/db/*.key to .gitignore"
echo "  2. Deploy certificates to production server"
echo "  3. Restart PostgreSQL container"
echo "  4. Update DATABASE_SSL_MODE=require in .env.production"
echo ""
echo "To verify SSL is working after restart:"
echo "  psql \"postgresql://janua:pass@localhost:5432/janua?sslmode=require\""
