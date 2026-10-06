# Multi-stage build (Task 5 enhancement).
#
# Dependencies are installed in throw-away builder stages and only the
# resulting site-packages are copied into slim runtime images. Each runtime
# image gets just the packages its script needs:
#
#   docker build -t diet-analysis .                    # default: data_analysis.py
#   docker build --target function -t diet-function .  # lambda_function.py

# ---------- builder: analysis dependencies ----------
FROM python:3.11-slim AS analysis-deps
COPY requirements-analysis.txt /tmp/
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements-analysis.txt

# ---------- builder: serverless function dependencies ----------
FROM python:3.11-slim AS function-deps
COPY requirements-function.txt /tmp/
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements-function.txt

# ---------- runtime: simulated serverless function ----------
FROM python:3.11-slim AS function
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=function-deps /install /usr/local
COPY lambda_function.py watch_and_process.py ./
CMD ["python", "lambda_function.py"]

# ---------- runtime: data analysis (last stage = default target) ----------
FROM python:3.11-slim AS analysis
ENV MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=analysis-deps /install /usr/local
COPY data_analysis.py ./
COPY data/ ./data/
CMD ["python", "data_analysis.py"]
