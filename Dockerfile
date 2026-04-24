# syntax=docker/dockerfile:1.1.7-experimental
#############################################
# Tox testsuite for multiple python version #
#############################################
FROM advian/tox-base:debian-bookworm as tox
ARG PYTHON_VERSIONS="3.11 3.12"
ARG UV_VERSION="0.11.6"
RUN export RESOLVED_VERSIONS=`pyenv_resolve $PYTHON_VERSIONS` \
    && echo RESOLVED_VERSIONS=$RESOLVED_VERSIONS \
    && for pyver in $RESOLVED_VERSIONS; do pyenv install -s $pyver; done \
    && pyenv global $RESOLVED_VERSIONS \
    && pip install -U "uv==$UV_VERSION" tox tox-uv \
    && apt-get update && apt-get install -y \
        git \
        ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y \
       docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/* \
    # Fix git runtime fatal:
    # unsafe repository ('/app' is owned by someone else)
    && git config --global --add safe.directory /app \
    && true

COPY . /app
WORKDIR /app
RUN uv sync --frozen \
    && uv run docker/pre_commit_init.sh \
    && true


######################
# Base builder image #
######################
FROM python:3.11-bookworm as builder_base
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /usr/local/bin/

ENV \
  # locale
  LC_ALL=C.UTF-8 \
  # python:
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  # pip:
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PIP_INDEX_URL=https://nexus.dev.pvarki.fi/repository/python/simple \
  # uv:
  UV_DEFAULT_INDEX=https://nexus.dev.pvarki.fi/repository/python/simple \
  UV_PROJECT_ENVIRONMENT=/.venv \
  UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y \
        curl \
        git \
        bash \
        build-essential \
        libffi-dev \
        libssl-dev \
        tini \
        openssh-client \
        cargo \
        libxmlsec1-openssl \
        libxmlsec1-dev \
        libxml2-dev \
        pkg-config \
        libpq-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    # githublab ssh
    && mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.com github.com | sort > ~/.ssh/known_hosts \
    && true

SHELL ["/bin/bash", "-lc"]


# Copy only requirements, to cache them in docker layer:
WORKDIR /pysetup
COPY ./uv.lock ./pyproject.toml ./README.rst /pysetup/
# Install runtime deps into the project venv (without installing the project itself yet)
RUN --mount=type=ssh uv venv /.venv \
    && echo 'source /.venv/bin/activate' >>/root/.profile \
    && uv sync --frozen --no-install-project --no-dev \
    && true


####################################
# Base stage for production builds #
####################################
FROM builder_base as production_build
# Copy entrypoint script
COPY ./docker/entrypoint.sh /docker-entrypoint.sh
COPY ./docker/container-init.sh /container-init.sh
# Only files needed by production setup
COPY ./uv.lock ./pyproject.toml ./README.rst /app/
COPY ./src /app/src
WORKDIR /app
# Build the wheel package with uv
RUN --mount=type=ssh source /.venv/bin/activate \
    && mkdir -p /tmp/wheelhouse \
    && uv build --wheel --out-dir /tmp/wheelhouse \
    && chmod a+x /docker-entrypoint.sh \
    && chmod a+x /container-init.sh \
    && true


#########################
# Main production build #
#########################
FROM python:3.11-slim-bookworm as production
COPY --from=production_build /tmp/wheelhouse /tmp/wheelhouse
COPY --from=production_build /docker-entrypoint.sh /docker-entrypoint.sh
COPY --from=production_build /container-init.sh /container-init.sh
WORKDIR /app
# Install system level deps for running the package (not devel versions for building wheels)
# and install the wheels we built in the previous step. generate default config
RUN --mount=type=ssh apt-get update && apt-get install -y \
        bash \
        libffi8 \
        tini \
        git \
        openssh-client \
        libpq5 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && chmod a+x /docker-entrypoint.sh \
    && WHEELFILE=`echo /tmp/wheelhouse/rasenmaeher_api-*.whl` \
    && pip3 install --index-url https://nexus.dev.pvarki.fi/repository/python/simple "$WHEELFILE"[all] \
    && rm -rf /tmp/wheelhouse/ \
    # Do whatever else you need to
    && true
ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]

FROM production as openapi
CMD ["rasenmaeher_api", "openapi"]


#####################################
# Base stage for development builds #
#####################################
FROM builder_base as devel_build
COPY . /app
WORKDIR /app
COPY ./docker/container-init.sh /container-init.sh
RUN --mount=type=ssh source /.venv/bin/activate \
    && apt-get update && apt-get install -y \
        git \
        ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y \
       docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --frozen \
    && true


#0############
# Run tests #
#############
FROM devel_build as test
COPY . /app
WORKDIR /app
ENTRYPOINT ["/usr/bin/tini", "--", "docker/entrypoint-test.sh"]
# Re run install to get the service itself installed
RUN --mount=type=ssh source /.venv/bin/activate \
    && uv sync --frozen \
    && docker/pre_commit_init.sh \
    && true


###########
# Hacking #
###########
FROM devel_build as devel_shell
# Copy everything to the image
COPY . /app
WORKDIR /app
RUN apt-get update && apt-get install -y zsh jq \
    && sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    && echo "source /root/.profile" >>/root/.zshrc \
    && pip3 install git-up \
    && echo "source /container-init.sh" >>/root/.profile \
    && true
ENTRYPOINT ["/bin/zsh", "-l"]
