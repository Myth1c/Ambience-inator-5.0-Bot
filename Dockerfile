# ---- Base Python image ----
FROM python:3.11-slim

# Install ffmpeg and other system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---- Working directory ----
WORKDIR /app

# ---- Copy code ----
COPY . .

# ---- Install dependencies ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Run the bot ----
CMD ["python3", "bot_runner.py"]
