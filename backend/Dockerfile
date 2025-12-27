FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    for i in 1 2 3; do \
        apt-get install -y ffmpeg && break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# Set working directory
WORKDIR /app

# Copy pyproject.toml
COPY pyproject.toml ./

# Install dependencies
RUN UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple uv pip install --system -e .

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/uploads /app/storage/audio /app/storage/temp

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]