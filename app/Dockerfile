FROM python:3.11-slim

WORKDIR /app

COPY app/ /app/app/
COPY scraper/ /app/scraper/
COPY background/ /app/background/

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /app/app/requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--client.toolbarMode=minimal"]
