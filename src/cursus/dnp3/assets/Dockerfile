FROM python:3.10-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYDNP3_URL=https://files.pythonhosted.org/packages/3d/7b/9da4115503bdce211323caaa12ad7a5128470366a62cdc9c3877549d0be5/pydnp3-0.1.0.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/pydnp3-build

RUN curl -L "$PYDNP3_URL" -o pydnp3-0.1.0.tar.gz \
    && tar -xzf pydnp3-0.1.0.tar.gz \
    && find pydnp3-0.1.0 \( -name 'CMakeLists.txt' -o -name '*.cmake' \) -type f -print0 \
      | xargs -0 sed -i \
        -e 's/cmake_minimum_required *(VERSION 2.8.12)/cmake_minimum_required(VERSION 3.5)/g' \
        -e 's/cmake_minimum_required *(VERSION 2.8)/cmake_minimum_required(VERSION 3.5)/g' \
        -e 's/cmake_minimum_required(VERSION 3.0)/cmake_minimum_required(VERSION 3.5)/g' \
    && find pydnp3-0.1.0/src -type f -print0 \
      | xargs -0 sed -i \
        -e 's#<python2\.7/Python\.h>#<Python.h>#g' \
    && pip install --no-cache-dir ./pydnp3-0.1.0

WORKDIR /app

COPY cursus /app/cursus
COPY cursus/dnp3/assets/run_server.py /app/run_server.py

ENV PYTHONPATH=/app
EXPOSE 20000

CMD ["python", "/app/run_server.py"]
