# Dockerfile for the main orchestrator service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by orchestrator's python packages (e.g., pyaudio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a requirements file for the orchestrator
COPY assistant/orchestrator_requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copy the entire application code
# This is broader than other services because the orchestrator
# interacts with many different parts of the codebase.
COPY . .

# The command is specified in docker-compose.yml, so no CMD is needed here.
# This allows for flexibility (e.g., running different commands for dev vs. prod).
