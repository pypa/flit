FROM mcr.microsoft.com/devcontainers/python:3

RUN python -m pip install --upgrade pip \
    && python -m pip install pytest pytest-cov \
    && python -m pip install 'flit>=3.8.0'

ENV FLIT_ROOT_INSTALL=1

COPY pyproject.toml README.rst ./
RUN mkdir -p flit \
    && python -m flit install --only-deps --deps develop \
    && rm -r pyproject.toml README.rst flit
