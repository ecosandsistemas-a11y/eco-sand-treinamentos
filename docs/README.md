# Eco Sand | Gestão de Treinamentos

Sistema web para controle de vencimento de treinamentos e cursos obrigatórios dos colaboradores da Eco Sand.

## Estrutura

- `app/server.py` — servidor HTTP (API + arquivos estáticos)
- `app/db.py` — schema SQLite e inicialização
- `app/models.py` — regras de negócio e cálculos
- `app/auth.py` — autenticação e permissões
- `app/import_xl.py` — importação da planilha Excel
- `app/static/` — interface web (HTML/CSS/JS)
- `data/ecosand.db` — banco de dados SQLite
- `google_drive/` — planilha original (referência)

## Como executar

```bash
cd /home/user/app
python3 server.py
```

Acesse http://localhost:8000

Login padrão: admin / admin123

## Tecnologias

Python 3 (stdlib) + SQLite. Sem dependências externas para execução.
Para importação da planilha, utiliza openpyxl (instalar: `pip install openpyxl`).

## Backup

Copie o arquivo `data/ecosand.db` e a pasta `uploads/` (anexos) para local seguro.
Restauração: substitua o arquivo `data/ecosand.db` pelo backup e reinicie o servidor.
'''