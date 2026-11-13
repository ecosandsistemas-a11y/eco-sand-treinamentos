import sqlite3, os, datetime, hashlib, secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))
DB_PATH = os.path.join(DATA_DIR, 'ecosand.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

SCHEMA = r'''
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  salt TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'consulta',
  nome TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS setores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE NOT NULL,
  descricao TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cargos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE NOT NULL,
  descricao TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS treinamentos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT,
  nome TEXT NOT NULL,
  descricao TEXT,
  categoria TEXT,
  prazo_validade_dias INTEGER,
  ativo INTEGER NOT NULL DEFAULT 1,
  observacoes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS colaboradores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT UNIQUE,
  nome TEXT NOT NULL,
  setor_id INTEGER,
  cargo_id INTEGER,
  matricula TEXT,
  data_admissao TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  situacao TEXT NOT NULL DEFAULT 'ativo',
  observacoes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by INTEGER,
  updated_by INTEGER,
  FOREIGN KEY (setor_id) REFERENCES setores(id),
  FOREIGN KEY (cargo_id) REFERENCES cargos(id)
);

CREATE TABLE IF NOT EXISTS realizacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  colaborador_id INTEGER NOT NULL,
  treinamento_id INTEGER NOT NULL,
  data_realizacao TEXT,
  prazo_validade_dias INTEGER,
  data_vencimento TEXT,
  setor_nome_hist TEXT,
  cargo_nome_hist TEXT,
  observacoes TEXT,
  origem TEXT DEFAULT 'manual',
  anexo_ref TEXT,
  registro_anterior_id INTEGER,
  created_at TEXT NOT NULL,
  created_by INTEGER,
  updated_at TEXT NOT NULL,
  updated_by INTEGER,
  FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id),
  FOREIGN KEY (treinamento_id) REFERENCES treinamentos(id)
);

CREATE TABLE IF NOT EXISTS auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  username TEXT,
  data_hora TEXT NOT NULL,
  tipo_operacao TEXT NOT NULL,
  entidade TEXT NOT NULL,
  registro_id INTEGER,
  campo TEXT,
  valor_anterior TEXT,
  valor_novo TEXT,
  motivo TEXT,
  origem TEXT
);

CREATE TABLE IF NOT EXISTS configuracoes (
  chave TEXT PRIMARY KEY,
  valor TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by INTEGER
);

CREATE TABLE IF NOT EXISTS pendencias_acomp (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  realizacao_id INTEGER NOT NULL UNIQUE,
  status_acomp TEXT DEFAULT 'pendente',
  observacao TEXT,
  responsavel TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (realizacao_id) REFERENCES realizacoes(id)
);

CREATE INDEX IF NOT EXISTS idx_realizacoes_colab ON realizacoes(colaborador_id);
CREATE INDEX IF NOT EXISTS idx_realizacoes_trein ON realizacoes(treinamento_id);
CREATE INDEX IF NOT EXISTS idx_realizacoes_venc ON realizacoes(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_colab_setor ON colaboradores(setor_id);
CREATE INDEX IF NOT EXISTS idx_colab_cargo ON colaboradores(cargo_id);
'''

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript(SCHEMA)
    # migration: add situacao column to colaboradores
    cols = [r[1] for r in conn.execute("PRAGMA table_info(colaboradores)").fetchall()]
    if 'situacao' not in cols:
        conn.execute("ALTER TABLE colaboradores ADD COLUMN situacao TEXT NOT NULL DEFAULT 'ativo'")
    conn.execute("UPDATE colaboradores SET situacao='inativo' WHERE ativo=0 AND situacao='ativo'")
    conn.execute("UPDATE colaboradores SET situacao='ativo' WHERE ativo=1 AND situacao NOT IN ('ativo','inativo','afastado')")
    cur = conn.execute("SELECT valor FROM configuracoes WHERE chave='janela_alerta_dias'")
    if cur.fetchone() is None:
        conn.execute("INSERT INTO configuracoes (chave,valor,updated_at) VALUES (?,?,?)",
                     ('janela_alerta_dias','30', now_iso()))
    cur = conn.execute("SELECT id FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        salt = secrets.token_hex(16)
        pw = 'admin123'
        h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex()
        conn.execute("INSERT INTO users (username,password_hash,salt,role,nome,ativo,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                     ('admin', h, salt, 'admin', 'Administrador', 1, now_iso(), now_iso()))
    conn.commit()
    conn.close()

def row_to_dict(row):
    return {k: row[k] for k in row.keys()} if row else None
