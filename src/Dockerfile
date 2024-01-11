# Globals and input args
FROM python:3.9.10-alpine3.15

WORKDIR /app

RUN pip3 install --upgrade pip

RUN apk add --no-cache gcc && \
    apk add libc-dev && \
    apk add build-base && \
    apk add libffi-dev

COPY requirements.txt ./

RUN pip3 install -r requirements.txt

# Install our code
COPY func_timeout/ ./func_timeout/
COPY *.py ./
COPY prom/ ./prom/
RUN chmod a+x /app/main.py

ENV PYTHONWARNINGS=ignore

# Setup our entrypoint command to run on docker run
CMD [ "python", "-u", "./main.py" ]
