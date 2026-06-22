FROM python:3.11-slim

# System deps: Tesseract (hin+eng), OpenCV headless, libGL for EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app
ENV PYTHONUNBUFFERED=1

EXPOSE 5001
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
