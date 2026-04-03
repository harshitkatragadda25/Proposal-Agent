FROM python:3.11-slim

# Set working directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6

# Copy requirements from parent directory
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy backend source code
COPY . .

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
