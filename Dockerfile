FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY polyquant ./polyquant
COPY web ./web
RUN pip install --no-cache-dir .
ENV POLYQUANT_DB_PATH=/data/polyquant.db
RUN mkdir -p /data
EXPOSE 8000
CMD ["python","-m","polyquant"]
