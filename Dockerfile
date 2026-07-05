FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Upgrade pip and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Default command to run the pipeline test script
CMD ["python", "scripts/run_pipeline_test.py"]
