FROM photoreserchgeo-backend:latest

WORKDIR /app

# Install additional packages for geo-research (opencv headless)
RUN pip install --no-cache-dir opencv-python-headless

COPY . .

EXPOSE 8765

CMD ["python", "web/server.py"]
