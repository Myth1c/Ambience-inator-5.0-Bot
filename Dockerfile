# ---- Base Python image ----
FROM python:3.11-slim

# ---- Working directory ----
WORKDIR /app

# ---- Copy code ----
COPY . .

# ---- Install dependencies ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Environment (optional defaults) ----
ENV PYTHONUNBUFFERED=1

# ---- Run the bot ----
CMD ["python3", "bot_runner.py"]
