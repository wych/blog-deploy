FROM python:3.7

WORKDIR /home/jim/
RUN apt-get update && apt-get install -y \
    git \
    hugo \
 && rm -rf /var/lib/apt/lists/*
COPY . /home/jim/
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "gunicorn", "main:app", "-b"]
CMD ["0.0.0.0:8080"]