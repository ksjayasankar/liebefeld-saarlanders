FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY navigator/__init__.py navigator/
# torchvision from the same CPU index as torch: the PyPI build docling pulls in does not match torch+cpu
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -e .
# headless Chromium for hosts marked render: browser (D-31)
RUN pip install --no-cache-dir -e ".[render]" && playwright install --with-deps --only-shell chromium
COPY . .
