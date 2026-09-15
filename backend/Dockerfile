# Backend image: FastAPI + the MCP server it spawns as a subprocess.
# Both run in this one container — the MCP server is not a separate service.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    EMBEDDING_MODEL=all-MiniLM-L6-v2

WORKDIR /app

# CPU-only torch, installed first and pinned.
#
# This is the single most important line in the file. sentence-transformers
# pulls torch transitively, and on Linux the PyPI wheel is the CUDA build: it
# drags in several GB of nvidia-* packages that never get used on a CPU
# instance. Installing the CPU wheel up front means the requirements install
# below sees torch already satisfied and leaves it alone.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Bake the embedding model into the image. Otherwise the first request after
# every deploy waits on an ~80MB download, and the host needs writable cache
# space at runtime.
RUN python -c "import os; from sentence_transformers import SentenceTransformer; \
    SentenceTransformer(os.environ['EMBEDDING_MODEL'])"

EXPOSE 8000

# Railway and Render inject $PORT; default to 8000 for local `docker run`.
# Use shell form (not JSON array) so $PORT gets expanded.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
