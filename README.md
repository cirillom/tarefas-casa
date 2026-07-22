# tarefas-casa

App simples de divisão de tarefas de casa. Frontend estático (`static/index.html`)
+ backend Flask/SQLite (`app.py`) que persiste tudo numa única tabela chave-valor.

## Desenvolver

```bash
docker compose up --build
```

Abre em `http://localhost:8000`. O SQLite fica em `./data-dev` (ignorado pelo git).
Como `app.py` é copiado na imagem, mudanças nele exigem `--build` de novo;
mudanças em `static/index.html` também, já que ele é copiado no build (não montado).

## Lançar uma versão

```bash
git tag v1.0.0
git push origin v1.0.0
```

Isso dispara `.github/workflows/release.yml`, que:
1. builda a imagem Docker,
2. publica em `ghcr.io/<seu-usuario>/tarefas-casa:latest` e `:v1.0.0`,
3. cria uma Release no GitHub anexando `docker-compose.example.yml`.

## Implantar no servidor

O servidor **não builda nada** — só puxa a imagem já pronta. Ver `docker-compose.example.yml`
para o compose de referência (é o que fica em `~/services/tarefas-casa/docker-compose.yml`).

Se o pacote no GHCR for privado, autentique uma vez no servidor:

```bash
echo "<PAT com escopo read:packages>" | docker login ghcr.io -u cirillom --password-stdin
```

## Atualizar depois de uma nova release

Sem Watchtower — é manual mesmo, dois comandos no servidor:

```bash
cd ~/services/tarefas-casa
docker compose pull
docker compose up -d
```

(`down` não é necessário: `up -d` já recria o container com a imagem nova sozinho.)
