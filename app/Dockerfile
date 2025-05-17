FROM python:3.9-slim
WORKDIR /app
# Copy requirements file
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy application code
COPY . .
# Set environment variables
ENV PORT=8080
# Add memory optimization environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Reduce connection pool size to save memory
ENV FIRESTORE_CONNECTION_POOL_SIZE=2 
# Expose port
EXPOSE 8080
# Use gunicorn with optimized settings
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 0 --worker-tmp-dir /dev/shm app:app