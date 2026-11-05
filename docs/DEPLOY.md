# Implantação (Render + GitHub)

## Repositório
1. Crie um repositório no GitHub e envie o conteúdo de `/home/user` (exceto `data/` se quiser banco novo).
2. Mantenha a estrutura: `app/`, `data/`, `docs/`.

## Render (Web Service)
- Build command: (nenhum, Python puro) — ou `pip install openpyxl` se quiser importação.
- Start command: `cd app && python3 server.py`
- Variável de ambiente: `PORT` (Render define automaticamente).
- Disco persistente: monte um disco em `/home/user/data` para persistir o SQLite.

## Observações
- O sistema usa SQLite. Para alta concorrência, considere migrar para PostgreSQL (ajustar db.py).
- Backups: copie `data/ecosand.db` periodicamente.
- O arquivo da planilha original pode ser importado via módulo Importação após o deploy.
'''