FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
WORKDIR /app
RUN pip install --no-cache-dir httpx==0.28.1 beautifulsoup4==4.14.2 playwright==1.55.0
COPY probe.py .
CMD ["python", "-u", "probe.py"]
