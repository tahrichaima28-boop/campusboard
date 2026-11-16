# CampusBoard - Mini-parcours DevOps

CampusBoard est un petit tableau d'annonces pour étudiants (objets perdus, covoiturage, cours à vendre), développé en **Flask + PostgreSQL**. L'application sert de support pour montrer un parcours DevOps complet : du code à la mise en ligne, de façon automatique, fiable et surveillée, avec des outils open-source gratuits.

## API

| Route | Rôle |
|---|---|
| `GET /health` | État de l'application (utilisé par Uptime Kuma) |
| `GET /posts` | Liste des annonces |
| `POST /posts` | Ajoute une annonce (`{"title": "...", "content": "..."}`) |

## Architecture

| Outil | Rôle | Port |
|---|---|---|
| GitLab CE (conteneur) | Code source, Merge Requests, CI/CD | 8081 |
| GitLab Runner (Ubuntu / WSL2, shell executor, tag `local`) | Exécute les jobs du pipeline | - |
| Registre Docker local (`registry:2`) | Stocke les images, tagguées avec le SHA du commit | 5000 |
| pyinfra (`deploy.py`) | Déploiement automatisé et idempotent | - |
| PostgreSQL (conteneur) | Base de données, volume persistant | 5432 (interne) |
| Application Flask (conteneur) | L'application | 3000 |
| Uptime Kuma (conteneur) | Supervision de `/health`, alertes Telegram | 3001 |

Remarque : le registre `registry:2` remplace Harbor (registre équivalent, autorisé par le sujet).

## Flux du pipeline

```mermaid
flowchart LR
    A[Branche feature/*] --> B[Merge Request]
    B --> C[test]
    C -->|test vert| D[Merge dans main]
    D --> E[build-image]
    E --> F[scan Trivy]
    F --> G[deploy pyinfra]
    G --> H[Uptime Kuma /health]
```

1. Le développeur travaille sur une branche `feature/*` (`main` est protégée : aucun push direct).
2. La Merge Request lance le job `test`. Un test qui échoue bloque la fusion (règle « Pipelines must succeed »).
3. La fusion dans `main` lance `build-image`, `scan` puis `deploy`.
4. `deploy.py` récupère la nouvelle image et redémarre l'application sans toucher à la base.
5. Uptime Kuma sonde `/health` et envoie une alerte Telegram en cas de panne.

## Pipeline (`.gitlab-ci.yml`)

| Stage | Quand | Rôle |
|---|---|---|
| `test` | Sur chaque push | Crée un venv, installe les dépendances et lance `pytest`. Un échec bloque la Merge Request. |
| `build-image` | `main` uniquement (`rules`) | Construit l'image Docker, la tague avec `$CI_COMMIT_SHORT_SHA` (traçabilité, rollback) et la pousse vers le registre local. |
| `scan` | `main` uniquement | Scan de vulnérabilités de l'image avec Trivy (HIGH, CRITICAL). |
| `deploy` | `main` uniquement | Lance `pyinfra -y @local deploy.py` avec le tag du commit. |

### Variables CI/CD (Settings > CI/CD > Variables)

`DB_USER`, `DB_PASSWORD` (masquée), `DB_NAME`. Aucun mot de passe n'est écrit dans le dépôt.

## Prérequis

- Docker Desktop (moteur démarré) et Git
- Ubuntu sous WSL2 (python3-venv, pip, curl, git) pour le runner
- Les conteneurs GitLab, registre et Uptime Kuma (commandes ci-dessous)

## Installation, étape par étape

### 1. Application seule (Docker Compose)

```bash
cp .env.example .env        # puis modifier DB_PASSWORD
docker compose up -d --build
curl http://localhost:3000/health
docker compose down
```

### 2. GitLab local

```bash
mkdir -p /d/devops/gitlab/{config,logs,data}
MSYS_NO_PATHCONV=1 docker run -d --hostname gitlab.local --name gitlab \
  -p 8081:8081 -p 2222:22 \
  -e GITLAB_OMNIBUS_CONFIG="external_url 'http://localhost:8081'" \
  -v D:/devops/gitlab/config:/etc/gitlab \
  -v D:/devops/gitlab/logs:/var/log/gitlab \
  -v D:/devops/gitlab/data:/var/opt/gitlab \
  --shm-size 256m gitlab/gitlab-ce:latest
docker update --restart unless-stopped gitlab
```

Premier démarrage : 3 à 5 minutes. Mot de passe root initial :

```bash
MSYS_NO_PATHCONV=1 docker exec gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

Puis : créer le projet `campusboard`, protéger `main` (push : No one, merge : Maintainers) et activer « Pipelines must succeed » (Settings > Merge requests).

### 3. Registre local

```bash
docker run -d --name registry --restart unless-stopped -p 5000:5000 -v registry-data:/var/lib/registry registry:2
curl http://localhost:5000/v2/_catalog
```

### 4. GitLab Runner (dans Ubuntu / WSL2)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip curl git
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
sudo chmod +x /usr/local/bin/gitlab-runner
gitlab-runner register --non-interactive --url http://localhost:8081/ --token <TOKEN_RUNNER> --executor shell --description local-shell-runner
gitlab-runner run
```

Le token vient de GitLab (Settings > CI/CD > Runners > New project runner, tag `local`).

### 5. Uptime Kuma

```bash
docker run -d --name uptime-kuma --restart unless-stopped -p 3001:3001 -v uptime-kuma-data:/app/data louislam/uptime-kuma:1
```

Dans http://localhost:3001 : créer le compte admin, ajouter un moniteur HTTP(s) sur `http://host.docker.internal:3000/health` (intervalle 60 s, 2 tentatives) et une notification Telegram (testée).

## Déploiement manuel (idempotent)

```bash
export DB_USER=... DB_PASSWORD=... DB_NAME=... TAG=<sha>
pyinfra -y @local deploy.py
```

Le script peut être relancé sans risque : le réseau et la base sont créés seulement s'ils sont absents, et les données restent dans le volume `campusboard-pgdata`.

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

## Démonstration

```bash
git checkout main && git pull gitlab main
./demo.sh
```

Le script modifie la version de l'application, pousse une branche, puis on crée la Merge Request. Après la fusion : test, build, scan et deploy s'enchaînent, l'application est mise à jour en moins de 5 minutes et Uptime Kuma la voit en ligne. Vérification : `curl http://localhost:3000/health`.

Test de panne : `docker stop campusboard-app` (Uptime Kuma passe au rouge et envoie une alerte Telegram), puis `docker start campusboard-app` (retour au vert).

## Sécurité

- `main` est protégée (push direct refusé, Merge Request obligatoire).
- Conteneur exécuté avec un utilisateur non-root (`appuser`), image multi-stage de moins de 200 Mo.
- Aucun secret dans le dépôt : `.env` est ignoré, les identifiants sont des variables CI/CD.
- Scan de l'image avec Trivy à chaque déploiement.
