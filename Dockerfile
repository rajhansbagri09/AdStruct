
FROM python:3.11-slim

WORKDIR /app

# Install Linux libraries required by OCR and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Make project packages importable
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PADDLE_PDX_CACHE_HOME=/root/.paddlex

# Create output directories
RUN mkdir -p outputs/uploads outputs/approved outputs/rejected

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
