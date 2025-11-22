FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including XML/SAML libraries for xmlsec
# Includes Node.js and npm for Prisma CLI, openssl for Prisma client generation
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    pkg-config \
    libxml2-dev \
    libxmlsec1-dev \
    libxslt-dev \
    libssl-dev \
    openssl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate Prisma Client (CRITICAL: Required for database access)
# Must run before switching to non-root user to ensure proper permissions
RUN cd /app && \
    if [ -f "../prisma/schema.prisma" ]; then \
        npm install -g prisma && \
        npx prisma generate --schema=../prisma/schema.prisma; \
    elif [ -f "../../prisma/schema.prisma" ]; then \
        npm install -g prisma && \
        npx prisma generate --schema=../../prisma/schema.prisma; \
    else \
        echo "Warning: Prisma schema not found, skipping generation"; \
    fi

# Create non-root user
RUN useradd -m -u 1000 janua && chown -R janua:janua /app
USER janua

# Expose port
EXPOSE 8000

# Run the application
# Use shell form to allow environment variable substitution
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
