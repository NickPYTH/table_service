FROM python:3.13
#FROM table_service-app:latest
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app
COPY table_service/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
ADD . /app/
WORKDIR /app/table_service/
RUN chmod +x run.sh

ENTRYPOINT ["/app/table_service/run.sh"]
