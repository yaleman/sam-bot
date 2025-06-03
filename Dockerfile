# Use the official Python image from the Docker Hub
FROM python:3.13-slim

# These two environment variables prevent __pycache__/ files.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

#RUN git clone https://github.com/yaleman/sam-bot /code/

WORKDIR /code

COPY ./ /code/


RUN pip install .


CMD ["sam-bot"]
