FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY vectorharbor ./vectorharbor
RUN pip install --no-cache-dir .
EXPOSE 8091
CMD ["uvicorn", "vectorharbor.main:app", "--host", "0.0.0.0", "--port", "8091"]
