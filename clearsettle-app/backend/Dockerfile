FROM python:3.11-slim-bookworm
WORKDIR /app

# System build deps + Chromium runtime libraries.
# Explicit package list avoids the 'ttf-unifont / ttf-ubuntu-font-family'
# failures that occur when playwright --with-deps runs on non-Ubuntu images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tooling (existing)
    libpq-dev gcc \
    # Chromium runtime deps
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \
    libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libglib2.0-0 \
    libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
    libxss1 libxtst6 libgdk-pixbuf2.0-0 libxkbcommon0 \
    # Fonts (subset — avoids unavailable ttf-unifont / ttf-ubuntu-font-family)
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Playwright's Chromium binary.
# System deps are already installed above, so --with-deps is intentionally omitted.
RUN playwright install chromium

COPY . .
RUN chmod +x start.sh

EXPOSE 8000

# start.sh: runs alembic migrations (if DATABASE_URL set) then starts uvicorn
CMD ["./start.sh"]
