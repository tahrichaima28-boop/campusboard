# CampusBoard - Mini-parcours DevOps

Petit tableau d'annonces pour etudiants (objets perdus, covoiturage, cours a vendre),
developpe en Flask + PostgreSQL. Il sert de support pour montrer un pipeline DevOps
complet, du code a la mise en ligne.

## API
| Route | Role |
|---|---|
| `GET /health` | Etat de l'application (utilise par Uptime Kuma) |
| `GET /posts` | Liste des annonces |
| `POST /posts` | Ajoute une annonce (`{"title": "...", "content": "..."}`) |

## Architecture
- **Application** : Flask + PostgreSQL
- **GitLab CE** (conteneur local) : code source, Merge Requests, CI/CD
- **GitLab Runner** (shell executor, tag `local`) : execute les jobs
- **Harbor** : registre prive d'images Docker
- **pyinfra** : script de deploiement (`deploy.py`)
- **Uptime Kuma** : supervision de `/health`

## Prerequis
Docker, Docker Compose, Python 3.12, Git, GitLab local + Runner, Harbor, Uptime Kuma.

## Lancer en local
```bash
cp .env.example .env      # puis modifier DB_PASSWORD
docker compose up -d --build
curl http://localhost:3000/health
curl -X POST http://localhost:3000/posts -H "Content-Type: application/json" -d '{"title":"Objet perdu","content":"Cle USB"}'
curl http://localhost:3000/posts
docker compose down
```

## Tests
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

## Pipeline (`.gitlab-ci.yml`)
```
feature/* -> Merge Request -> test -> merge dans main -> build -> scan -> deploy
```
| Stage | Role |
|---|---|
| `test` | Lance pytest sur chaque push. Un test qui echoue bloque la Merge Request. |
| `build` | Sur `main` seulement : construit l'image, la tague avec `$CI_COMMIT_SHORT_SHA`, la pousse vers Harbor. |
| `scan` | Scan de vulnerabilites de l'image avec Trivy. |
| `deploy` | Lance `deploy.py` (pyinfra) : pull de l'image, remplacement du conteneur, verification de `/health`. |

## Variables GitLab CI/CD (Settings > CI/CD > Variables)
`HARBOR_USER`, `HARBOR_PASSWORD`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (masquees, aucun secret dans le depot).

## Deploiement manuel
```bash
export DB_USER=... DB_PASSWORD=... DB_NAME=... TAG=<sha>
pyinfra @local deploy.py
```
Le script est idempotent : on peut le relancer, la base et ses donnees sont conservees (volume `campusboard-pgdata`).

## Supervision
Uptime Kuma (http://localhost:3001) : monitor HTTP sur `http://localhost:3000/health`, notification configuree.

## Demo
`./demo.sh` montre le cycle : modification, branche, push, Merge Request, pipeline, deploiement.

Projet realise dans le cadre du module DevOps.
