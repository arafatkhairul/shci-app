# Step 1: Python base image with CUDA 12.6 support for Ubuntu 24.04
FROM nvidia/cuda:12.6.0-devel-ubuntu24.04

# Step 2: Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    build-essential gcc g++ make \
    portaudio19-dev libasound2-dev \
    ffmpeg libsndfile1 \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y python3.11 python3.11-dev python3.11-venv python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.11 /usr/bin/python

# Step 3: Install PyTorch with CUDA 12.6 support
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Step 3: Working directory set kora
WORKDIR /app

# Step 4: Proyojoniyo package gulo copy kora
COPY ./requirements.txt /app/requirements.txt

# Step 5: Python package gulo install kora with caching to speed up future builds
RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip setuptools wheel \
    && pip install --default-timeout=100 --no-cache-dir -r /app/requirements.txt

# Step 6: Shompurno project code copy kora
COPY . /app

# Step 7: Application kon port e cholbe sheta bole deya
EXPOSE 8000

# Step 8: Application chalate Uvicorn ke command deya with production settings
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log"]
