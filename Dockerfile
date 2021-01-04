FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "/bin/sh", "-c", "echo Container started ;  while sleep 1; do :; done" ]