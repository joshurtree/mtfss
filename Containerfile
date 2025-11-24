# MTFSS - Multi-Tenant Folder Sorting Sieve Container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (if they exist) and install Python dependencies
# Note: Add requirements.txt if needed for additional dependencies
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY mtfss.py .

# Create non-root user for security
RUN useradd -m -u 1000 mtfss && \
    chown -R mtfss:mtfss /app
USER mtfss

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check to ensure the application is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import mtfss; print('OK')" || exit 1

# Default command - runs the MTFSS processor
# Override with environment variables or command line arguments
CMD ["python", "mtfss.py"]

# Example usage:
# Build: podman build -t mtfss .
# Run: podman run -e IMAP_SERVER=imap.gmail.com \
#                 -e IMAP_USERNAME=user@gmail.com \
#                 -e IMAP_PASSWORD=your_password \
#                 -e PRIMARY_DOMAIN=gmail.com \
#                 mtfss

# For development with custom arguments:
# podman run -it mtfss python mtfss.py --server imap.example.com \
#                                      --username user@example.com \
#                                      --domain example.com \
#                                      --once