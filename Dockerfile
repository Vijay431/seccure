# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Seccure"
LABEL org.opencontainers.image.description="Automated npm security vulnerability fixer using LangChain"
LABEL org.opencontainers.image.source="https://github.com/owner/seccure"

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install curl, git, bash, docker.io
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        ca-certificates \
        bash \
        docker.io \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Run as non-root user for security
RUN useradd --create-home --shell /bin/bash seccure
USER seccure
WORKDIR /home/seccure/app

# Install nvm and a default node version (v20)
ENV NVM_DIR="/home/seccure/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install 20 \
    && nvm alias default 20

# Install Python dependencies first (cached layer)
COPY --chown=seccure:seccure requirements.txt .
ENV PATH="/home/seccure/app/.venv/bin:${PATH}"
RUN uv venv && uv pip install -r requirements.txt

# Copy agent source
COPY --chown=seccure:seccure src/ ./src/

CMD ["python", "src/main.py"]
