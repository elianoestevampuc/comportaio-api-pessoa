FROM ubuntu:latest

LABEL maintainer="Eliano Estevam"

RUN apt-get update && apt-get upgrade -y

RUN apt-get install python3 python3-pip python3-venv git -y

RUN git clone -b main https://github.com/elianoestevampuc/comportaio-api-pessoa.git /opt/comportaio/

WORKDIR /opt/comportaio/

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip3 install -r requirements.txt 

RUN python3 -m flask && python3 -m flask && python3 -m flask

ENV FLASK_APP=app.py
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8000"]