FROM apache/airflow:3.3.2-python3.11

COPY --chown=airflow:root pyproject.toml README.md ./
COPY --chown=airflow:root src ./src

RUN pip install --no-cache-dir -e .
