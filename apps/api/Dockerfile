FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including XML/SAML libraries for xmlsec
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    pkg-config \
    libxml2-dev \
    libxmlsec1-dev \
    libxslt-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 plinto && chown -R plinto:plinto /app
USER plinto

# Expose port
EXPOSE 8000

# Run the application
# Use shell form to allow environment variable substitution
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]