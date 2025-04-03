FROM python:3.11-slim
ENV PYTHONPATH="${PYTHONPATH}:/app"

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "bot/main.py"]