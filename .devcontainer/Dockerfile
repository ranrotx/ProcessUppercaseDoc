FROM mcr.microsoft.com/devcontainers/python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Install Python development tools
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
    black \
    flake8 \
    pytest \
    pytest-cov \
    mypy \
    isort

# Set up AWS CLI configuration directory
RUN mkdir -p /home/$USERNAME/.aws \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.aws

# Switch to non-root user
USER $USERNAME

# Set up shell
SHELL ["/bin/bash", "-c"]

# Set working directory
WORKDIR /workspace 