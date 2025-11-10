FROM python:3.14-slim
WORKDIR /backend
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT ["python"]
CMD ["main.py"]