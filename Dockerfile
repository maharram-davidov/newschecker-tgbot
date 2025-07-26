# Multi-stage build for production NewsChecker
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r newschecker && useradd -r -g newschecker newschecker

# Create application directory
WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R newschecker:newschecker /app

# Copy application code
COPY --chown=newschecker:newschecker . .

# Create startup script
RUN echo '#!/bin/bash\n\
if [ "$1" = "bot" ]; then\n\
    exec python bot.py\n\
elif [ "$1" = "web" ]; then\n\
    exec python web_interface.py\n\
else\n\
    echo "Usage: $0 {bot|web}"\n\
    exit 1\n\
fi' > /app/start.sh && \
    chmod +x /app/start.sh && \
    chown newschecker:newschecker /app/start.sh

# Switch to non-root user
USER newschecker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port for web interface
EXPOSE 5000

# Default command
CMD ["./start.sh", "bot"]

# Labels for metadata
LABEL maintainer="NewsChecker Team" \
      version="2.0.0" \
      description="AI-powered news verification bot for Azerbaijani content" \
      org.opencontainers.image.source="https://github.com/your-org/newschecker" 