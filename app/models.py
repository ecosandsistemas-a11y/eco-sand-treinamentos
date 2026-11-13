import db, datetime, json

def parse_date(s):
    if s is None or s == '':
        return None
    s = str(s).strip()
    # try ISO
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    # excel serial
    try:
        n = float(s)
        # excel serial date
        base = datetime.date(1899,12,30)
        return (base + datetime.timedelta(days=int(n))).isoformat()
    except Exception:
        return None

def fmt_date(s):
    if not s: return ''
    try:
        d = datetime.date.fromisoformat(s)
        return d.strftime('%d/%m/%Y')
    except Exception:
        return str(s)

def janela_alerta():
    conn = db.get_conn()
    row = conn.execute("SELECT valor FROM configuracoes WHERE chave='janela_alerta_dias'").fetchone()
    conn.close()
    try:
        return int(row['valor']) if row else 30
    except Exception:
        return 30

def set_janela_alerta(val, user_id=None):
    conn = db.get_conn()
    conn.execute("INSERT INTO configuracoes (chave,valor,updated_at,updated_by) VALUES (?,?,?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, updated_at=excluded.updated_at, updated_by=excluded.updated_by",
                 ('janela_alerta_dias', str(val), db.now_iso(), user_id))
    conn.commit()
    conn.close()

def calc_vencimento(data_realizacao, prazo_dias):
    if not data_realizacao or prazo_dias is None:
        return None
    try:
        d = datetime.date.fromisoformat(data_realizacao)
        return (d + datetime.timedelta(days=int(prazo_dias))).isoformat()
    except Exception:
        return None

def status_de(vencimento, janela=None):
    if janela is None:
        janela = janela_alerta()
    if not vencimento:
        return 'dados_incompletos'
    try:
        v = datetime.date.fromisoformat(vencimento)
    except Exception:
        return 'dados_incompletos'
    hoje = datetime.date.today()
    if v < hoje:
        return 'vencido'
    if v < hoje + datetime.timedelta(days=janela):
        return 'proximo'
    return 'em_dia'

STATUS_LABEL = {
    'em_dia': 'Treinamento em dia',
    'proximo': 'Próximo do vencimento',
    'vencido': 'Treinamento Vencido',
    'dados_incompletos': 'Dados incompletos',
}

def dias_restantes(vencimento):
    if not vencimento: return None
    try:
        v = datetime.date.fromisoformat(vencimento)
        return (v - datetime.date.today()).days
    except Exception:
        return None

# ---------- setores ----------
def list_setores(apenas_ativos=False):
    conn = db.get_conn()
    q = "SELECT * FROM setores"
    if apenas_ativos: q += " WHERE ativo=1"
    q += " ORDER BY nome"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [db.row_to_dict(r) for r in rows]

def get_setor(id):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM setores WHERE id=?", (id,)).fetchone()
    conn.close()
    return db.row_to_dict(r)

def create_setor(nome, descricao=None, user_id=None):
    nome = nome.strip()
    conn = db.get_conn()
    try:
        conn.execute("INSERT INTO setores (nome,descricao,ativo,created_at,updated_at) VALUES (?,?,?,?,?)",
                     (nome, descricao, 1, db.now_iso(), db.now_iso()))
        conn.commit()
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        conn.close()
        return None, 'Já existe um setor com esse nome.'
    conn.close()
    audit(user_id, 'criacao', 'setor', sid, None, None, nome, None, 'manual')
    return sid, None

def update_setor(id, nome, descricao=None, ativo=None, user_id=None):
    conn = db.get_conn()
    old = conn.execute("SELECT * FROM setores WHERE id=?", (id,)).fetchone()
    if not old:
        conn.close(); return False, 'Não encontrado.'
    sets=[]; params=[]
    if nome is not None:
        sets.append('nome=?'); params.append(nome.strip())
    if descricao is not None:
        sets.append('descricao=?'); params.append(descricao)
    if ativo is not None:
        sets.append('ativo=?'); params.append(1 if ativo else 0)
    if 'situacao' in data and data.get('situacao') is not None:
        # sync ativo flag
        sets.append('ativo=?'); params.append(1 if data['situacao']=='ativo' else 0)
    sets.append('updated_at=?'); params.append(db.now_iso())
    params.append(id)
    try:
        conn.execute(f"UPDATE setores SET {','.join(sets)} WHERE id=?", params)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); return False, 'Nome duplicado.'
    conn.close()
    audit(user_id, 'edicao', 'setor', id, old['nome'], nome, None, 'manual')
    return True, None

# ---------- cargos ----------
def list_cargos(apenas_ativos=False):
    conn = db.get_conn()
    q = "SELECT * FROM cargos"
    if apenas_ativos: q += " WHERE ativo=1"
    q += " ORDER BY nome"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [db.row_to_dict(r) for r in rows]

def get_cargo(id):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM cargos WHERE id=?", (id,)).fetchone()
    conn.close()
    return db.row_to_dict(r)

def create_cargo(nome, descricao=None, user_id=None):
    nome = nome.strip()
    conn = db.get_conn()
    try:
        conn.execute("INSERT INTO cargos (nome,descricao,ativo,created_at,updated_at) VALUES (?,?,?,?,?)",
                     (nome, descricao, 1, db.now_iso(), db.now_iso()))
        conn.commit()
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        conn.close(); return None, 'Já existe um cargo com esse nome.'
    conn.close()
    audit(user_id, 'criacao', 'cargo', sid, None, None, nome, None, 'manual')
    return sid, None

def update_cargo(id, nome, descricao=None, ativo=None, user_id=None):
    conn = db.get_conn()
    old = conn.execute("SELECT * FROM cargos WHERE id=?", (id,)).fetchone()
    if not old: conn.close(); return False,'Não encontrado.'
    sets=[]; params=[]
    if nome is not None: sets.append('nome=?'); params.append(nome.strip())
    if descricao is not None: sets.append('descricao=?'); params.append(descricao)
    if ativo is not None: sets.append('ativo=?'); params.append(1 if ativo else 0)
    if 'situacao' in data and data.get('situacao') is not None:
        # sync ativo flag
        sets.append('ativo=?'); params.append(1 if data['situacao']=='ativo' else 0)
    sets.append('updated_at=?'); params.append(db.now_iso())
    params.append(id)
    try:
        conn.execute(f"UPDATE cargos SET {','.join(sets)} WHERE id=?", params)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); return False,'Nome duplicado.'
    conn.close()
    audit(user_id,'edicao','cargo',id,'nome',old['nome'],nome,None,'manual')
    return True,None

# ---------- treinamentos ----------
def list_treinamentos(apenas_ativos=False):
    conn = db.get_conn()
    q = "SELECT * FROM treinamentos"
    if apenas_ativos: q += " WHERE ativo=1"
    q += " ORDER BY nome"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [db.row_to_dict(r) for r in rows]

def get_treinamento(id):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM treinamentos WHERE id=?", (id,)).fetchone()
    conn.close()
    return db.row_to_dict(r)

def create_treinamento(nome, codigo=None, descricao=None, categoria=None, prazo=None, observacoes=None, user_id=None):
    nome = nome.strip()
    conn = db.get_conn()
    try:
        conn.execute("""INSERT INTO treinamentos (codigo,nome,descricao,categoria,prazo_validade_dias,ativo,observacoes,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                     (codigo, nome, descricao, categoria, prazo, 1, observacoes, db.now_iso(), db.now_iso()))
        conn.commit()
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        conn.close(); return None,'Erro de integridade.'
    conn.close()
    audit(user_id,'criacao','treinamento',sid,None,None,nome,None,'manual')
    return sid,None

def update_treinamento(id, data, user_id=None):
    conn = db.get_conn()
    old = conn.execute("SELECT * FROM treinamentos WHERE id=?", (id,)).fetchone()
    if not old: conn.close(); return False,'Não encontrado.'
    fields = ['codigo','nome','descricao','categoria','prazo_validade_dias','ativo','observacoes']
    sets=[]; params=[]
    for f in fields:
        if f in data and data[f] is not None:
            sets.append(f+'=?')
            params.append(data[f])
    if 'situacao' in data and data.get('situacao') is not None:
        # sync ativo flag
        sets.append('ativo=?'); params.append(1 if data['situacao']=='ativo' else 0)
    sets.append('updated_at=?'); params.append(db.now_iso())
    params.append(id)
    conn.execute(f"UPDATE treinamentos SET {','.join(sets)} WHERE id=?", params)
    conn.commit()
    conn.close()
    audit(user_id,'edicao','treinamento',id,'nome',old['nome'],data.get('nome',old['nome']),None,'manual')
    return True,None

# ---------- colaboradores ----------
def list_colaboradores(filtros=None):
    conn = db.get_conn()
    q = """SELECT c.*, s.nome AS setor_nome, g.nome AS cargo_nome
           FROM colaboradores c
           LEFT JOIN setores s ON s.id=c.setor_id
           LEFT JOIN cargos g ON g.id=c.cargo_id
           WHERE 1=1"""
    params=[]
    if filtros:
        if filtros.get('ativo') is not None:
            if filtros['ativo']:
                q += " AND c.situacao='ativo'"
            else:
                q += " AND c.situacao!='ativo'"
        if filtros.get('situacao'):
            q += " AND c.situacao=?"; params.append(filtros['situacao'])
        if filtros.get('setor_id'):
            q += " AND c.setor_id=?"; params.append(filtros['setor_id'])
        if filtros.get('cargo_id'):
            q += " AND c.cargo_id=?"; params.append(filtros['cargo_id'])
        if filtros.get('busca'):
            q += " AND (LOWER(c.nome) LIKE ? OR LOWER(c.codigo) LIKE ?)"; b='%'+filtros['busca'].lower()+'%'; params += [b,b]
    q += " ORDER BY c.nome"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [db.row_to_dict(r) for r in rows]

def get_colaborador(id):
    conn = db.get_conn()
    r = conn.execute("""SELECT c.*, s.nome AS setor_nome, g.nome AS cargo_nome
                        FROM colaboradores c
                        LEFT JOIN setores s ON s.id=c.setor_id
                        LEFT JOIN cargos g ON g.id=c.cargo_id
                        WHERE c.id=?""", (id,)).fetchone()
    conn.close()
    return db.row_to_dict(r)

def create_colaborador(data, user_id=None):
    conn = db.get_conn()
    try:
        conn.execute("""INSERT INTO colaboradores (codigo,nome,setor_id,cargo_id,matricula,data_admissao,ativo,situacao,observacoes,created_at,updated_at,created_by,updated_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (data.get('codigo'), data['nome'].strip(), data.get('setor_id'), data.get('cargo_id'),
                      data.get('matricula'), data.get('data_admissao'), 1 if (data.get('situacao', data.get('ativo',1) and 'ativo' or 'inativo')=='ativo') else 0,
                      data.get('situacao', 'ativo' if data.get('ativo',1) else 'inativo'),
                      data.get('observacoes'), db.now_iso(), db.now_iso(), user_id, user_id))
        conn.commit()
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError as e:
        conn.close(); return None, 'Código já existente ou erro de integridade: '+str(e)
    conn.close()
    audit(user_id,'criacao','colaborador',sid,None,None,data['nome'],None,'manual')
    return sid,None

def update_colaborador(id, data, user_id=None):
    conn = db.get_conn()
    old = conn.execute("SELECT * FROM colaboradores WHERE id=?", (id,)).fetchone()
    if not old: conn.close(); return False,'Não encontrado.'
    fields = ['codigo','nome','setor_id','cargo_id','matricula','data_admissao','ativo','situacao','observacoes']
    sets=[]; params=[]
    for f in fields:
        if f in data:
            sets.append(f+'=?')
            v = data[f]
            if f=='ativo' and v is not None: v = 1 if v else 0
            if f=='nome' and v is not None: v = v.strip()
            params.append(v)
    if 'situacao' in data and data.get('situacao') is not None:
        # sync ativo flag
        sets.append('ativo=?'); params.append(1 if data['situacao']=='ativo' else 0)
    sets.append('updated_at=?'); params.append(db.now_iso())
    sets.append('updated_by=?'); params.append(user_id)
    params.append(id)
    try:
        conn.execute(f"UPDATE colaboradores SET {','.join(sets)} WHERE id=?", params)
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close(); return False,'Erro: '+str(e)
    conn.close()
    audit(user_id,'edicao','colaborador',id,'nome',old['nome'],data.get('nome',old['nome']),None,'manual')
    return True,None

# ---------- realizacoes ----------
def create_realizacao(data, user_id=None, username=None):
    conn = db.get_conn()
    # validate
    colab = conn.execute("SELECT * FROM colaboradores WHERE id=?", (data['colaborador_id'],)).fetchone()
    trein = conn.execute("SELECT * FROM treinamentos WHERE id=?", (data['treinamento_id'],)).fetchone()
    if not colab or not trein:
        conn.close(); return None,'Colaborador ou treinamento inválido.'
    data_real = parse_date(data.get('data_realizacao'))
    prazo = data.get('prazo_validade_dias')
    if prazo is not None and prazo != '':
        try: prazo = int(prazo)
        except: prazo = None
    else:
        prazo = trein['prazo_validade_dias'] if trein['prazo_validade_dias'] is not None else None
        # if user explicitly passed empty, keep None
        if 'prazo_validade_dias' in data and (data['prazo_validade_dias'] is None or data['prazo_validade_dias']==''):
            prazo = None
    venc = calc_vencimento(data_real, prazo)
    # historical setor/cargo
    setor_hist = colab_setor_name(conn, colab['id']) if False else None
    # get setor name
    srow = conn.execute("SELECT nome FROM setores WHERE id=?", (colab['setor_id'],)).fetchone() if colab['setor_id'] else None
    crow = conn.execute("SELECT nome FROM cargos WHERE id=?", (colab['cargo_id'],)).fetchone() if colab['cargo_id'] else None
    setor_nome = srow['nome'] if srow else None
    cargo_nome = crow['nome'] if crow else None
    conn.execute("""INSERT INTO realizacoes (colaborador_id,treinamento_id,data_realizacao,prazo_validade_dias,data_vencimento,
                    setor_nome_hist,cargo_nome_hist,observacoes,origem,anexo_ref,registro_anterior_id,created_at,created_by,updated_at,updated_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (data['colaborador_id'], data['treinamento_id'], data_real, prazo, venc,
                  setor_nome, cargo_nome, data.get('observacoes'), data.get('origem','manual'),
                  data.get('anexo_ref'), data.get('registro_anterior_id'),
                  db.now_iso(), user_id, db.now_iso(), user_id))
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    audit(user_id, 'criacao', 'realizacao', rid, None, None, f"colab={data['colaborador_id']} trein={data['treinamento_id']}", data.get('motivo'), data.get('origem','manual'), username=username)
    return rid, None

def colab_setor_name(conn, colab_id):
    return None

def update_realizacao(id, data, user_id=None, username=None, motivo=None):
    conn = db.get_conn()
    old = conn.execute("SELECT * FROM realizacoes WHERE id=?", (id,)).fetchone()
    if not old: conn.close(); return False,'Não encontrado.'
    data_real = parse_date(data.get('data_realizacao', old['data_realizacao']))
    prazo = data.get('prazo_validade_dias', old['prazo_validade_dias'])
    if prazo is not None and prazo != '':
        try: prazo = int(prazo)
        except: prazo = old['prazo_validade_dias']
    else:
        prazo = None
    venc = calc_vencimento(data_real, prazo)
    sets=[]; params=[]
    sets.append('data_realizacao=?'); params.append(data_real)
    sets.append('prazo_validade_dias=?'); params.append(prazo)
    sets.append('data_vencimento=?'); params.append(venc)
    if 'observacoes' in data:
        sets.append('observacoes=?'); params.append(data['observacoes'])
    if 'anexo_ref' in data:
        sets.append('anexo_ref=?'); params.append(data['anexo_ref'])
    if 'situacao' in data and data.get('situacao') is not None:
        # sync ativo flag
        sets.append('ativo=?'); params.append(1 if data['situacao']=='ativo' else 0)
    sets.append('updated_at=?'); params.append(db.now_iso())
    sets.append('updated_by=?'); params.append(user_id)
    params.append(id)
    conn.execute(f"UPDATE realizacoes SET {','.join(sets)} WHERE id=?", params)
    conn.commit()
    conn.close()
    # audit field changes
    if old['data_realizacao'] != data_real:
        audit(user_id, 'edicao', 'realizacao', id, 'data_realizacao', old['data_realizacao'], data_real, motivo, 'manual', username=username)
    if old['prazo_validade_dias'] != prazo:
        audit(user_id, 'edicao', 'realizacao', id, 'prazo_validade_dias', old['prazo_validade_dias'], prazo, motivo, 'manual', username=username)
    if old['data_vencimento'] != venc:
        audit(user_id, 'edicao', 'realizacao', id, 'data_vencimento', old['data_vencimento'], venc, motivo, 'manual', username=username)
    return True, None

def delete_realizacao(id, user_id=None, username=None):
    conn = db.get_conn()
    conn.execute("DELETE FROM realizacoes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    audit(user_id, 'exclusao', 'realizacao', id, None, None, None, 'manual', username=username)
    return True

def get_realizacao(id):
    conn = db.get_conn()
    r = conn.execute("""SELECT r.*, c.nome AS colaborador_nome, t.nome AS treinamento_nome
                        FROM realizacoes r
                        JOIN colaboradores c ON c.id=r.colaborador_id
                        JOIN treinamentos t ON t.id=r.treinamento_id
                        WHERE r.id=?""", (id,)).fetchone()
    conn.close()
    d = db.row_to_dict(r)
    if d:
        d['status'] = status_de(d['data_vencimento'])
        d['status_label'] = STATUS_LABEL[d['status']]
        d['dias'] = dias_restantes(d['data_vencimento'])
        d['data_realizacao_fmt'] = fmt_date(d['data_realizacao'])
        d['data_vencimento_fmt'] = fmt_date(d['data_vencimento'])
    return d

def list_realizacoes(filtros=None):
    conn = db.get_conn()
    q = """SELECT r.*, c.nome AS colaborador_nome, c.ativo AS colaborador_ativo, c.situacao AS colaborador_situacao,
                  t.nome AS treinamento_nome, t.ativo AS treinamento_ativo,
                  s.nome AS setor_nome, g.nome AS cargo_nome
           FROM realizacoes r
           JOIN colaboradores c ON c.id=r.colaborador_id
           JOIN treinamentos t ON t.id=r.treinamento_id
           LEFT JOIN setores s ON s.id=c.setor_id
           LEFT JOIN cargos g ON g.id=c.cargo_id
           WHERE 1=1"""
    params=[]
    if filtros:
        if filtros.get('colaborador_id'):
            q += " AND r.colaborador_id=?"; params.append(filtros['colaborador_id'])
        if filtros.get('treinamento_id'):
            q += " AND r.treinamento_id=?"; params.append(filtros['treinamento_id'])
        if filtros.get('setor_id'):
            q += " AND c.setor_id=?"; params.append(filtros['setor_id'])
        if filtros.get('cargo_id'):
            q += " AND c.cargo_id=?"; params.append(filtros['cargo_id'])
        if filtros.get('ano'):
            q += " AND substr(r.data_vencimento,1,4)=?"; params.append(str(filtros['ano']))
        if filtros.get('mes'):
            q += " AND substr(r.data_vencimento,6,2)=?"; params.append(str(filtros['mes']).zfill(2))
        if filtros.get('colab_ativo') is not None:
            q += " AND c.ativo=?"; params.append(1 if filtros['colab_ativo'] else 0)
        if filtros.get('excluir_afastados'):
            q += " AND c.situacao!='afastado'" 
        if filtros.get('busca'):
            b='%'+filtros['busca'].lower()+'%'
            q += " AND (LOWER(c.nome) LIKE ? OR LOWER(t.nome) LIKE ?)"; params += [b,b]
        if filtros.get('data_inicio'):
            q += " AND r.data_vencimento >= ?"; params.append(filtros['data_inicio'])
        if filtros.get('data_fim'):
            q += " AND r.data_vencimento <= ?"; params.append(filtros['data_fim'])
    q += " ORDER BY r.data_vencimento, c.nome"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    out=[]
    for r in rows:
        d = db.row_to_dict(r)
        d['status'] = status_de(d['data_vencimento'])
        d['status_label'] = STATUS_LABEL[d['status']]
        d['dias'] = dias_restantes(d['data_vencimento'])
        d['data_realizacao_fmt'] = fmt_date(d['data_realizacao'])
        d['data_vencimento_fmt'] = fmt_date(d['data_vencimento'])
        out.append(d)
    # filter by status if requested
    if filtros and filtros.get('status'):
        out = [d for d in out if d['status']==filtros['status']]
    return out

def latest_realizacao(colaborador_id, treinamento_id):
    conn = db.get_conn()
    rows = conn.execute("""SELECT * FROM realizacoes WHERE colaborador_id=? AND treinamento_id=? ORDER BY data_realizacao DESC, id DESC""",
                        (colaborador_id, treinamento_id)).fetchall()
    conn.close()
    if not rows: return None
    # check tie
    if len(rows)>=2 and rows[0]['data_realizacao']==rows[1]['data_realizacao']:
        return ('tie', [db.row_to_dict(r) for r in rows[:2]])
    return db.row_to_dict(rows[0])

def realizacoes_por_colaborador(colaborador_id):
    # for each treinamento, latest realizacao
    conn = db.get_conn()
    treins = conn.execute("SELECT DISTINCT treinamento_id FROM realizacoes WHERE colaborador_id=?", (colaborador_id,)).fetchall()
    conn.close()
    out=[]
    for t in treins:
        tid = t['treinamento_id']
        lr = latest_realizacao(colaborador_id, tid)
        if isinstance(lr, tuple):
            # tie -> return both flagged
            for r in lr[1]:
                d2 = dict(r)
                tr = get_treinamento(d2['treinamento_id'])
                d2['treinamento_nome'] = tr['nome'] if tr else ''
                d2['status']=status_de(d2['data_vencimento'])
                d2['status_label']=STATUS_LABEL[d2['status']]
                d2['dias']=dias_restantes(d2['data_vencimento'])
                d2['data_realizacao_fmt']=fmt_date(d2['data_realizacao'])
                d2['data_vencimento_fmt']=fmt_date(d2['data_vencimento'])
                d2['tie']=True
                out.append(d2)
            continue
        if lr:
            d = dict(lr)
            d['status']=status_de(d['data_vencimento'])
            d['status_label']=STATUS_LABEL[d['status']]
            d['dias']=dias_restantes(d['data_vencimento'])
            d['data_realizacao_fmt']=fmt_date(d['data_realizacao'])
            d['data_vencimento_fmt']=fmt_date(d['data_vencimento'])
            d['tie']=False
            # attach treinamento nome
            tr = get_treinamento(d['treinamento_id'])
            d['treinamento_nome']=tr['nome'] if tr else ''
            out.append(d)
    return out

def historico_realizacoes(colaborador_id, treinamento_id):
    conn = db.get_conn()
    rows = conn.execute("""SELECT r.*, c.nome AS colaborador_nome, t.nome AS treinamento_nome
                           FROM realizacoes r JOIN colaboradores c ON c.id=r.colaborador_id
                           JOIN treinamentos t ON t.id=r.treinamento_id
                           WHERE r.colaborador_id=? AND r.treinamento_id=? ORDER BY r.data_realizacao, r.id""",
                        (colaborador_id, treinamento_id)).fetchall()
    conn.close()
    out=[]
    for r in rows:
        d=db.row_to_dict(r)
        d['status']=status_de(d['data_vencimento'])
        d['status_label']=STATUS_LABEL[d['status']]
        d['dias']=dias_restantes(d['data_vencimento'])
        d['data_realizacao_fmt']=fmt_date(d['data_realizacao'])
        d['data_vencimento_fmt']=fmt_date(d['data_vencimento'])
        out.append(d)
    return out

# ---------- dashboard ----------
def dashboard(filtros=None):
    regs = list_realizacoes(filtros or {})
    total = len(regs)
    em_dia = sum(1 for r in regs if r['status']=='em_dia')
    proximo = sum(1 for r in regs if r['status']=='proximo')
    vencido = sum(1 for r in regs if r['status']=='vencido')
    incompleto = sum(1 for r in regs if r['status']=='dados_incompletos')
    # colaboradores afetados
    colabs_venc = set(r['colaborador_id'] for r in regs if r['status']=='vencido')
    colabs_prox = set(r['colaborador_id'] for r in regs if r['status']=='proximo')
    pct_dia = round(em_dia/total*100,1) if total else 0
    pct_venc = round(vencido/total*100,1) if total else 0
    # vencimentos proximos 7/15/30
    hoje = datetime.date.today()
    def within(n):
        c=0
        for r in regs:
            if r['data_vencimento']:
                try:
                    v=datetime.date.fromisoformat(r['data_vencimento'])
                    if hoje <= v <= hoje+datetime.timedelta(days=n):
                        c+=1
                except: pass
        return c
    # por setor
    por_setor = {}
    for r in regs:
        key = r.get('setor_nome') or 'Sem setor'
        por_setor.setdefault(key, {'setor':key,'total':0,'em_dia':0,'proximo':0,'vencido':0,'incompleto':0})
        por_setor[key]['total']+=1
        por_setor[key][r['status'] if r['status']!='dados_incompletos' else 'incompleto'] = por_setor[key].get(r['status'] if r['status']!='dados_incompletos' else 'incompleto',0)+1
    # por cargo
    por_cargo = {}
    for r in regs:
        key = r.get('cargo_nome') or 'Sem cargo'
        por_cargo.setdefault(key, {'cargo':key,'total':0,'em_dia':0,'proximo':0,'vencido':0,'incompleto':0})
        por_cargo[key]['total']+=1
        st = r['status'] if r['status']!='dados_incompletos' else 'incompleto'
        por_cargo[key][st]+=1
    # por treinamento pendencias
    por_trein = {}
    for r in regs:
        if r['status'] in ('vencido','proximo','dados_incompletos'):
            key = r.get('treinamento_nome') or ''
            por_trein[key] = por_trein.get(key,0)+1
    # vencimentos por mes (ano atual/filtro)
    por_mes = {m:0 for m in range(1,13)}
    for r in regs:
        if r['data_vencimento']:
            try:
                v=datetime.date.fromisoformat(r['data_vencimento'])
                por_mes[v.month]+=1
            except: pass
    # por ano
    por_ano = {}
    for r in regs:
        if r['data_vencimento']:
            y = r['data_vencimento'][:4]
            por_ano[y] = por_ano.get(y,0)+1
    # vencimentos por dia do mes (para relatorio mensal) handled separately
    # prioridades
    prio = sorted([r for r in regs if r['status'] in ('vencido','proximo')], key=lambda x: (0 if x['status']=='vencido' else 1, x['data_vencimento'] or '9999'))
    return {
        'total': total, 'em_dia': em_dia, 'proximo': proximo, 'vencido': vencido, 'incompleto': incompleto,
        'colabs_vencido': len(colabs_venc), 'colabs_proximo': len(colabs_prox),
        'pct_dia': pct_dia, 'pct_vencido': pct_venc,
        'prox_7': within(7), 'prox_15': within(15), 'prox_30': within(30),
        'por_setor': list(por_setor.values()),
        'por_cargo': list(por_cargo.values()),
        'por_trein_pend': sorted([{'treinamento':k,'qtd':v} for k,v in por_trein.items()], key=lambda x:-x['qtd']),
        'por_mes': [{'mes':m,'qtd':por_mes[m]} for m in range(1,13)],
        'por_ano': [{'ano':k,'qtd':v} for k,v in sorted(por_ano.items())],
        'prioridades': prio[:50],
    }

# ---------- audit ----------
def audit(user_id, tipo_operacao, entidade, registro_id, campo=None, valor_anterior=None, valor_novo=None, motivo=None, origem='manual', username=None):
    conn = db.get_conn()
    if username is None and user_id:
        u = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        username = u['username'] if u else None
    conn.execute("""INSERT INTO auditoria (user_id,username,data_hora,tipo_operacao,entidade,registro_id,campo,valor_anterior,valor_novo,motivo,origem)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                 (user_id, username, db.now_iso(), tipo_operacao, entidade, registro_id, campo,
                  None if valor_anterior is None else str(valor_anterior),
                  None if valor_novo is None else str(valor_novo), motivo, origem))
    conn.commit()
    conn.close()

def list_audit(filtros=None, limit=200):
    conn = db.get_conn()
    q = "SELECT * FROM auditoria WHERE 1=1"
    params=[]
    if filtros:
        if filtros.get('entidade'): q+=" AND entidade=?"; params.append(filtros['entidade'])
        if filtros.get('user_id'): q+=" AND user_id=?"; params.append(filtros['user_id'])
    q += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [db.row_to_dict(r) for r in rows]

# ---------- pendencias acompanhamento ----------
def marcar_acompanhada(realizacao_id, status, observacao=None, responsavel=None):
    conn = db.get_conn()
    existing = conn.execute("SELECT id FROM pendencias_acomp WHERE realizacao_id=?", (realizacao_id,)).fetchone()
    if existing:
        conn.execute("UPDATE pendencias_acomp SET status_acomp=?,observacao=?,responsavel=?,updated_at=? WHERE realizacao_id=?",
                     (status, observacao, responsavel, db.now_iso(), realizacao_id))
    else:
        conn.execute("INSERT INTO pendencias_acomp (realizacao_id,status_acomp,observacao,responsavel,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     (realizacao_id, status, observacao, responsavel, db.now_iso(), db.now_iso()))
    conn.commit()
    conn.close()

def get_acomp(realizacao_id):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM pendencias_acomp WHERE realizacao_id=?", (realizacao_id,)).fetchone()
    conn.close()
    return db.row_to_dict(r)
