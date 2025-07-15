# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set up and install build-time dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
RUN poetry install --no-interaction --no-ansi --no-root --no-dev

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime-only system dependencies
RUN apt-get update && apt-get install -y libpq5 curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from the builder stage to the system site-packages
COPY --from=builder /root/.cache/pypoetry/virtualenvs/*-py3.11/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy executables from the builder stage
COPY --from=builder /root/.cache/pypoetry/virtualenvs/*-py3.11/bin /usr/local/bin

# Copy the application code
COPY . .

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

# Run the application without --reload for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 