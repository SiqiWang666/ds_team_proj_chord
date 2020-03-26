FROM python:alpine3.7

WORKDIR /usr/app

COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "server.py"]