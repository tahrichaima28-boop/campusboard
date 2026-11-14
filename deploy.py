# deploy.py - deploiement idempotent de CampusBoard (pyinfra)
# Variables d'environnement requises : DB_USER, DB_PASSWORD, DB_NAME
# Optionnelles : TAG (defaut: latest), HARBOR_USER, HARBOR_PASSWORD
import os

from pyinfra.operations import server

tag = os.environ.get("TAG", "latest")
image = f"localhost/devops/campusboard:{tag}"
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]
db_name = os.environ["DB_NAME"]
harbor_user = os.environ.get("HARBOR_USER")
harbor_password = os.environ.get("HARBOR_PASSWORD")

if harbor_user and harbor_password:
    server.shell(
        name="Login Harbor",
        commands=[f'echo "{harbor_password}" | docker login localhost -u "{harbor_user}" --password-stdin'],
    )

server.shell(
    name="Reseau Docker",
    commands=["docker network create campusboard-net 2>/dev/null || true"],
)

server.shell(
    name="Base de donnees (creee seulement si absente, donnees conservees)",
    commands=[
        "docker start campusboard-db 2>/dev/null || "
        "docker run -d --name campusboard-db --network campusboard-net --restart unless-stopped "
        f"-e POSTGRES_USER={db_user} -e POSTGRES_PASSWORD={db_password} -e POSTGRES_DB={db_name} "
        "-v campusboard-pgdata:/var/lib/postgresql/data postgres:16-alpine",
    ],
)

server.shell(name="Pull de l'image", commands=[f"docker pull {image}"])

server.shell(
    name="Remplacer le conteneur de l'application",
    commands=[
        "docker rm -f campusboard-app || true",
        "docker run -d --name campusboard-app --network campusboard-net -p 3000:3000 "
        "--restart unless-stopped "
        f"-e DB_HOST=campusboard-db -e DB_USER={db_user} -e DB_PASSWORD={db_password} -e DB_NAME={db_name} "
        f"{image}",
    ],
)

server.shell(
    name="Verifier /health",
    commands=[
        "for i in $(seq 1 20); do curl -sf http://localhost:3000/health && exit 0; sleep 2; done; exit 1"
    ],
)
