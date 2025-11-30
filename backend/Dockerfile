#FROM python:3.13
#ENV PYTHONUNBUFFERED 1
#FROM table-service-app-base313:latest
FROM 10.47.0.221:5000/table_service_api-app:v1
#RUN mkdir /app
WORKDIR /app
#COPY table_service/requirements.txt .
#RUN pip install --upgrade pip && pip install -r requirements.txt
ADD table_service .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]