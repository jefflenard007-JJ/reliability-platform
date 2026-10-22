# Multi-stage build: small, non-root runtime image
FROM python:3.12-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Patch OS packages, then remove pip/setuptools/wheel and the bundled ensurepip wheels:
# the app never installs anything at runtime, so packaging tools are only attack surface.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip setuptools wheel \
    && rm -rf /usr/local/lib/python3.12/ensurepip /usr/local/bin/pip* \
    && find /usr/local/lib/python3.12 -name "setuptools*" -prune -exec rm -rf {} +
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=build /install /usr/local
COPY src/ ./
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
