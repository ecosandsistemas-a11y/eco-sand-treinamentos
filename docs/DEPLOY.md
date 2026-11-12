# Implantação (Render + GitHub)

## Repositório (GitHub)
1. Crie um repositório vazio no GitHub (ex.: `eco-sand-treinamentos`).
2. No terminal, dentro de `/home/user`:
   ```bash
   git remote add origin https://github.com/SEU_USUARIO/eco-sand-treinamentos.git
   git branch -M main
   git push -u origin main
   ```
3. Mantenha a estrutura: `app/`, `data/`, `docs/`, `requirements.txt`, `Procfile`, `render.yaml`.

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