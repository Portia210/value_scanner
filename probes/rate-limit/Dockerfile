FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir "httpx[http2]==0.28.1" beautifulsoup4==4.14.2
COPY probe.py .
CMD ["python", "-u", "probe.py"]
