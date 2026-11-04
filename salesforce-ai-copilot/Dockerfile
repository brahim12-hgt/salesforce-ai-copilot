FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN cd ml && (test -f ../data/raw/sales_pipeline.csv && python prepare_maven.py --raw ../data/raw || (python make_fixture.py && python prepare_maven.py --raw ../data/raw_sample)) && python train.py
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
