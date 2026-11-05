# AcademiaCloud - imagem única para web, init, publicador e notificacoes (Grupo 1).
# Multi-stage: "frontend" compila o React com Node (o Node NÃO vai para a imagem final);
# o estágio "deps" instala as dependências em um venv; a imagem final
# copia só o venv e o código, sem cache do pip nem ferramentas de build.

# ---------- estágio 0: frontend React + shadcn/ui (só o build estático vai para a imagem)
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- estágio 1: dependências
FROM python:3.12-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# venv SEM pip: o pip do sistema instala dentro dele (pip --python). Assim a imagem
# final não carrega uma segunda cópia do pip (~17 MB).
RUN python -m venv --without-pip /opt/venv
COPY requirements.txt .
# requirements.txt é copiado antes do código: alterar o código não invalida esta camada (cache).
RUN pip --python /opt/venv/bin/python install -r requirements.txt

# ---------- estágio 2: testes (docker build --target test .)
FROM deps AS test
WORKDIR /srv
COPY app ./app
COPY --from=frontend /fe/dist ./app/static
COPY tests ./tests
ENV NOTIF_SCHEMA=""
RUN /opt/venv/bin/python -m unittest discover -s tests -v

# ---------- estágio 3: imagem final
FROM python:3.12-slim AS final
LABEL org.opencontainers.image.title="AcademiaCloud" \
      org.opencontainers.image.description="Estudo de caso Docker + Computação em Nuvem"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
WORKDIR /srv
COPY --from=deps /opt/venv /opt/venv
# Usuário sem privilégios (Grupo 3): o processo não roda como root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin academic
COPY --chown=root:root app ./app
COPY --from=frontend --chown=root:root /fe/dist ./app/static
USER academic
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "app.wsgi:app"]
