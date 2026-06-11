FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PORT=8501
EXPOSE $PORT
CMD streamlit run dashboard/app.py --server.port $PORT --server.enableCORS=false
