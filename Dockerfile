FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code files
COPY . .

# Expose port
EXPOSE 3000

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
