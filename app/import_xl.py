import openpyxl, db, models, os, datetime

def read_workbook(path):
    return openpyxl.load_workbook(path, data_only=True)

def preview(path):
    wb = read_workbook(path)
    ws = wb['CAD1']
    # colaboradores rows 6.. (until empty name)
    colabs = []
    setores_set = set()
    cargos_set = set()
    treins_set = set()
    r = 6
    while True:
        name = ws.cell(row=r, column=4).value
        if name is None or str(name).strip() == '':
            # check if any further? stop at first empty run? We'll stop
            # but ensure not skip: if next has data, continue; here simple stop
            # check next 5
            nxt = [ws.cell(row=r+i, column=4).value for i in range(1,6)]
            if all(v is None or str(v).strip()=='' for v in nxt):
                break
            r += 1
            continue
        name = str(name).strip()
        setor = ws.cell(row=r, column=7).value
        cargo = ws.cell(row=r, column=10).value
        if setor is not None and str(setor).strip() != '':
            setores_set.add(str(setor).strip())
        if cargo is not None and str(cargo).strip() != '':
            cargos_set.add(str(cargo).strip())
        colabs.append({'nome': name, 'setor': (str(setor).strip() if setor is not None else None),
                       'cargo': (str(cargo).strip() if cargo is not None else None)})
        r += 1
    # treinamentos: column M rows 6.. until empty
    r = 6
    while True:
        t = ws.cell(row=r, column=13).value
        if t is None or str(t).strip() == '':
            nxt = [ws.cell(row=r+i, column=13).value for i in range(1,6)]
            if all(v is None or str(v).strip()=='' for v in nxt):
                break
            r += 1
            continue
        treins_set.add(str(t).strip())
        r += 1

    # LANC1
    ws2 = wb['LANC1']
    lancs = []
    r = 6
    while True:
        name = ws2.cell(row=r, column=4).value
        if name is None or str(name).strip() == '':
            nxt = [ws2.cell(row=r+i, column=4).value for i in range(1,6)]
            if all(v is None or str(v).strip()=='' for v in nxt):
                break
            r += 1
            continue
        trein = ws2.cell(row=r, column=7).value
        data_real = ws2.cell(row=r, column=8).value
        prazo = ws2.cell(row=r, column=9).value
        obs = ws2.cell(row=r, column=13).value
        lancs.append({
            'colaborador': str(name).strip(),
            'cargo': (str(ws2.cell(row=r,column=5).value).strip() if ws2.cell(row=r,column=5).value is not None else None),
            'setor': (str(ws2.cell(row=r,column=6).value).strip() if ws2.cell(row=r,column=6).value is not None else None),
            'treinamento': (str(trein).strip() if trein is not None else None),
            'data_realizacao': _excel_date(data_real),
            'prazo': (int(prazo) if prazo is not None and str(prazo).strip()!='' else None),
            'observacoes': (str(obs).strip() if obs is not None else None),
        })
        r += 1

    # warnings
    warnings = []
    # colaboradores in lancs not in colabs
    colab_names = set(c['nome'] for c in colabs)
    for l in lancs:
        if l['colaborador'] not in colab_names:
            warnings.append(f"Colaborador '{l['colaborador']}' do lançamento não consta no cadastro.")
    trein_names = treins_set
    for l in lancs:
        if l['treinamento'] and l['treinamento'] not in trein_names:
            warnings.append(f"Treinamento '{l['treinamento']}' do lançamento não consta no cadastro.")
    # duplicidades de realizacao
    seen = set()
    dup = 0
    for l in lancs:
        key = (l['colaborador'], l['treinamento'], l['data_realizacao'], l['prazo'])
        if key in seen: dup += 1
        seen.add(key)
    if dup:
        warnings.append(f"{dup} lançamentos duplicados idênticos no arquivo.")

    return {
        'setores': sorted(setores_set),
        'cargos': sorted(cargos_set),
        'treinamentos': sorted(treins_set),
        'colaboradores': colabs,
        'lancamentos': lancs,
        'totais': {
            'setores': len(setores_set),
            'cargos': len(cargos_set),
            'treinamentos': len(treins_set),
            'colaboradores': len(colabs),
            'lancamentos': len(lancs),
        },
        'warnings': warnings[:50],
        'warnings_count': len(warnings),
    }

def _excel_date(v):
    if v is None: return None
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    s = str(v).strip()
    if s == '': return None
    # try
    for fmt in ('%Y-%m-%d','%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        n = float(s)
        base = datetime.date(1899,12,30)
        return (base + datetime.timedelta(days=int(n))).isoformat()
    except Exception:
        return None

def commit(path, user_id=None, username=None):
    data = preview(path)
    conn = db.get_conn()
    # setores
    setor_map = {}
    for s in data['setores']:
        row = conn.execute("SELECT id FROM setores WHERE nome=?", (s,)).fetchone()
        if row:
            setor_map[s] = row['id']
        else:
            conn.execute("INSERT INTO setores (nome,descricao,ativo,created_at,updated_at) VALUES (?,?,?,?,?)",
                         (s, None, 1, db.now_iso(), db.now_iso()))
            setor_map[s] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # cargos
    cargo_map = {}
    for c in data['cargos']:
        row = conn.execute("SELECT id FROM cargos WHERE nome=?", (c,)).fetchone()
        if row:
            cargo_map[c] = row['id']
        else:
            conn.execute("INSERT INTO cargos (nome,descricao,ativo,created_at,updated_at) VALUES (?,?,?,?,?)",
                         (c, None, 1, db.now_iso(), db.now_iso()))
            cargo_map[c] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # treinamentos
    trein_map = {}
    for t in data['treinamentos']:
        row = conn.execute("SELECT id FROM treinamentos WHERE nome=?", (t,)).fetchone()
        if row:
            trein_map[t] = row['id']
        else:
            conn.execute("""INSERT INTO treinamentos (codigo,nome,descricao,categoria,prazo_validade_dias,ativo,observacoes,created_at,updated_at)
                            VALUES (?,?,?,?,?,?,?,?,?)""",
                         (None, t, None, None, None, 1, None, db.now_iso(), db.now_iso()))
            trein_map[t] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # colaboradores
    colab_map = {}
    for c in data['colaboradores']:
        row = conn.execute("SELECT id FROM colaboradores WHERE nome=?", (c['nome'],)).fetchone()
        sid = setor_map.get(c['setor']) if c['setor'] else None
        cid = cargo_map.get(c['cargo']) if c['cargo'] else None
        if row:
            colab_map[c['nome']] = row['id']
            # update setor/cargo if missing
            conn.execute("UPDATE colaboradores SET setor_id=COALESCE(setor_id,?), cargo_id=COALESCE(cargo_id,?), updated_at=? WHERE id=?",
                         (sid, cid, db.now_iso(), row['id']))
        else:
            conn.execute("""INSERT INTO colaboradores (codigo,nome,setor_id,cargo_id,matricula,data_admissao,ativo,observacoes,created_at,updated_at,created_by,updated_by)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (None, c['nome'], sid, cid, None, None, 1, None, db.now_iso(), db.now_iso(), user_id, user_id))
            colab_map[c['nome']] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    # realizações
    imported = 0
    skipped = 0
    for l in data['lancamentos']:
        cname = l['colaborador']
        tname = l['treinamento']
        if cname not in colab_map or tname not in trein_map:
            skipped += 1
            continue
        colab_id = colab_map[cname]
        trein_id = trein_map[tname]
        data_real = l['data_realizacao']
        prazo = l['prazo']
        # idempotency: check existing identical
        existing = conn.execute("""SELECT id FROM realizacoes WHERE colaborador_id=? AND treinamento_id=? AND data_realizacao IS ? AND prazo_validade_dias IS ?""",
                                (colab_id, trein_id, data_real, prazo)).fetchone()
        if existing:
            skipped += 1
            continue
        # setor/cargo hist from launch
        setor_hist = l['setor']
        cargo_hist = l['cargo']
        venc = models.calc_vencimento(data_real, prazo)
        conn.execute("""INSERT INTO realizacoes (colaborador_id,treinamento_id,data_realizacao,prazo_validade_dias,data_vencimento,
                        setor_nome_hist,cargo_nome_hist,observacoes,origem,created_at,created_by,updated_at,updated_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (colab_id, trein_id, data_real, prazo, venc, setor_hist, cargo_hist, l['observacoes'],
                      'importacao', db.now_iso(), user_id, db.now_iso(), user_id))
        imported += 1
    conn.commit()
    conn.close()
    models.audit(user_id, 'importacao', 'sistema', None, None, None, f"importados={imported} ignorados={skipped}", None, 'importacao', username=username)
    return {'importados': imported, 'ignorados': skipped, 'totais': data['totais']}
