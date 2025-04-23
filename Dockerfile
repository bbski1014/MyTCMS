# Dockerfile for PostgreSQL with pgvector
# Start from the official PostgreSQL 16 image
FROM postgres:16

# Switch to root user to install packages
USER root

# Install required packages and add PostgreSQL APT repository GPG key and source list
# Instructions adapted from https://www.postgresql.org/download/linux/debian/
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    lsb-release \
    ca-certificates && \
    # Import PostgreSQL GPG key
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    # Add PostgreSQL repository
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    # Update package list again after adding the repository
    apt-get update && \
    # Install pgvector for PostgreSQL 16
    apt-get install -y --no-install-recommends postgresql-16-pgvector && \
    # Clean up APT caches to reduce image size
    rm -rf /var/lib/apt/lists/*

# Switch back to the default postgres user
USER postgres