FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements from parent directory
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy frontend source code
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
