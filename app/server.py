import http.server, socketserver, json, os, urllib.parse, mimetypes, db, models, auth, import_xl, datetime, hashlib

PORT = int(os.environ.get('PORT', '8000'))
BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'static')

db.init_db()

def json_resp(handler, code, obj):
    data = json.dumps(obj, default=str, ensure_ascii=False).encode('utf-8')
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def read_body(handler):
    n = int(handler.headers.get('Content-Length', 0))
    raw = handler.rfile.read(n) if n else b''
    if not raw: return {}
    try:
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return {}

def get_token(handler):
    cookie = handler.headers.get('Cookie', '')
    for part in cookie.split(';'):
        part = part.strip()
        if part.startswith('session='):
            return part.split('=',1)[1]
    # also allow Authorization header
    authh = handler.headers.get('Authorization','')
    if authh.startswith('Bearer '):
        return authh[7:]
    return None

def current_user(handler):
    u = auth.get_user_by_token(get_token(handler))
    if u:
        return u
    return None

def require_auth(handler):
    u = current_user(handler)
    if not u:
        json_resp(handler, 401, {'error': 'Não autenticado'})
        return None
    if not u.get('ativo'):
        json_resp(handler, 403, {'error': 'Usuário inativo'})
        return None
    return u

def require_perm(handler, u, perm):
    if not auth.has_perm(u, perm):
        json_resp(handler, 403, {'error': 'Sem permissão'})
        return False
    return True

def add_cors(handler):
    origin = handler.headers.get('Origin')
    if origin:
        handler.send_header('Access-Control-Allow-Origin', origin)
        handler.send_header('Access-Control-Allow-Credentials', 'true')
    handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def end_headers(self):
        try:
            add_cors(self)
        except Exception:
            pass
        super().end_headers()

    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def route(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        qs = urllib.parse.parse_qs(parsed.query)
        self.qs = qs
        # static
        if method == 'GET' and (path == '/' or path.startswith('/static/')):
            self.serve_static(path)
            return
        # API
        if path.startswith('/api/'):
            try:
                self.handle_api(method, path, qs)
            except Exception as e:
                import traceback; traceback.print_exc()
                try:
                    json_resp(self, 500, {'error': str(e)})
                except Exception:
                    pass
            return
        # fallback index
        self.serve_static('/')

    def serve_static(self, path):
        if path == '/':
            path = '/static/index.html'
        elif not path.startswith('/static/'):
            path = '/static/index.html'
        fpath = os.path.join(BASE, path.lstrip('/'))
        if not os.path.isfile(fpath):
            fpath = os.path.join(STATIC, 'index.html')
        try:
            with open(fpath, 'rb') as f:
                data = f.read()
        except Exception:
            self.send_response(404); self.end_headers(); return
        ctype = mimetypes.guess_type(fpath)[0] or 'application/octet-stream'
        if fpath.endswith('.html'): ctype = 'text/html; charset=utf-8'
        if fpath.endswith('.js'): ctype = 'application/javascript; charset=utf-8'
        if fpath.endswith('.css'): ctype = 'text/css; charset=utf-8'
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_api(self, method, path, qs):
        # auth endpoints
        if path == '/api/login' and method == 'POST':
            body = read_body(self)
            username = (body.get('username') or '').strip()
            pw = body.get('password') or ''
            conn = db.get_conn()
            row = conn.execute("SELECT * FROM users WHERE username=? AND ativo=1", (username,)).fetchone()
            conn.close()
            if not row or not auth.verify_password(pw, row['password_hash'], row['salt']):
                json_resp(self, 401, {'error': 'Usuário ou senha inválidos'})
                return
            remember = bool(body.get('remember'))
            token = auth.create_session(row['id'], remember=remember)
            u = db.row_to_dict(row)
            maxage = 30*24*3600 if remember else 7*24*3600
            # set cookie
            self.send_response(200)
            data = json.dumps({'user': {'id':u['id'],'username':u['username'],'role':u['role'],'nome':u['nome']}, 'token': token}).encode()
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Set-Cookie', f'session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={maxage}')
            self.end_headers()
            self.wfile.write(data)
            return
        if path == '/api/logout' and method == 'POST':
            t = get_token(self)
            if t: auth.delete_session(t)
            data = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Set-Cookie','session=; Path=/; Max-Age=0')
            self.end_headers()
            self.wfile.write(data)
            self.wfile.write(b'{"ok":true}')
            return
        if path == '/api/me' and method == 'GET':
            u = current_user(self)
            if not u:
                json_resp(self, 401, {'error':'not auth'}); return
            json_resp(self, 200, {'user': {'id':u['id'],'username':u['username'],'role':u['role'],'nome':u['nome']}})
            return

        # all below require auth
        u = require_auth(self)
        if not u: return

        # ---- setores ----
        if path == '/api/setores':
            if method == 'GET':
                json_resp(self, 200, models.list_setores())
                return
            if method == 'POST':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                sid, err = models.create_setor(body.get('nome',''), body.get('descricao'), u['id'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': sid})
                return
        if path.startswith('/api/setores/'):
            sid = int(path.split('/')[-1])
            if method == 'PUT':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                ok, err = models.update_setor(sid, body.get('nome'), body.get('descricao'), body.get('ativo'), u['id'])
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return
            if method == 'DELETE':
                if not require_perm(self, u, 'delete'): return
                models.update_setor(sid, None, None, False, u['id'])
                json_resp(self, 200, {'ok': True})
                return

        # ---- cargos ----
        if path == '/api/cargos':
            if method == 'GET':
                json_resp(self, 200, models.list_cargos())
                return
            if method == 'POST':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                sid, err = models.create_cargo(body.get('nome',''), body.get('descricao'), u['id'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': sid})
                return
        if path.startswith('/api/cargos/'):
            cid = int(path.split('/')[-1])
            if method == 'PUT':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                ok, err = models.update_cargo(cid, body.get('nome'), body.get('descricao'), body.get('ativo'), u['id'])
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return

        # ---- treinamentos ----
        if path == '/api/treinamentos':
            if method == 'GET':
                json_resp(self, 200, models.list_treinamentos())
                return
            if method == 'POST':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                sid, err = models.create_treinamento(body.get('nome',''), body.get('codigo'), body.get('descricao'),
                                                     body.get('categoria'), body.get('prazo_validade_dias'), body.get('observacoes'), u['id'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': sid})
                return
        if path.startswith('/api/treinamentos/'):
            tid = int(path.split('/')[-1])
            if method == 'PUT':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                ok, err = models.update_treinamento(tid, body, u['id'])
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return
            if method == 'GET':
                t = models.get_treinamento(tid)
                json_resp(self, 200, t or {})
                return

        # ---- colaboradores ----
        if path == '/api/colaboradores':
            if method == 'GET':
                filtros = {}
                if qs.get('busca'): filtros['busca'] = qs['busca'][0]
                if qs.get('setor_id'): filtros['setor_id'] = int(qs['setor_id'][0])
                if qs.get('cargo_id'): filtros['cargo_id'] = int(qs['cargo_id'][0])
                if qs.get('ativo'): filtros['ativo'] = (qs['ativo'][0] == '1')
                if qs.get('situacao'): filtros['situacao'] = qs['situacao'][0]
                json_resp(self, 200, models.list_colaboradores(filtros))
                return
            if method == 'POST':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                sid, err = models.create_colaborador(body, u['id'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': sid})
                return
        if path.startswith('/api/colaboradores/') and path.endswith('/ficha'):
            cid = int(path.split('/')[-2])
            if method == 'GET':
                c = models.get_colaborador(cid)
                regs = models.realizacoes_por_colaborador(cid)
                ags = [a for a in models.list_agendamentos({'colaborador_id': cid}) if a['status']=='agendado']
                json_resp(self, 200, {'colaborador': c, 'realizacoes': regs, 'agendamentos': ags})
                return
        if path.startswith('/api/colaboradores/'):
            cid = int(path.split('/')[-1])
            if method == 'GET':
                json_resp(self, 200, models.get_colaborador(cid) or {})
                return
            if method == 'PUT':
                if not require_perm(self, u, 'cadastros'): return
                body = read_body(self)
                try:
                    ok, err = models.update_colaborador(cid, body, u['id'])
                except Exception as e:
                    import traceback; traceback.print_exc()
                    json_resp(self, 500, {'error': str(e)}); return
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return

        # ---- realizacoes ----
        if path == '/api/realizacoes':
            if method == 'GET':
                filtros = {}
                for k in ['colaborador_id','treinamento_id','setor_id','cargo_id','ano','mes','status','busca','data_inicio','data_fim']:
                    if qs.get(k): filtros[k] = qs[k][0]
                if qs.get('colab_ativo'): filtros['colab_ativo'] = (qs['colab_ativo'][0]=='1')
                if filtros.get('colaborador_id'): filtros['colaborador_id']=int(filtros['colaborador_id'])
                if filtros.get('treinamento_id'): filtros['treinamento_id']=int(filtros['treinamento_id'])
                if filtros.get('setor_id'): filtros['setor_id']=int(filtros['setor_id'])
                if filtros.get('cargo_id'): filtros['cargo_id']=int(filtros['cargo_id'])
                json_resp(self, 200, models.list_realizacoes(filtros))
                return
            if method == 'POST':
                if not require_perm(self, u, 'realizacoes'): return
                body = read_body(self)
                rid, err = models.create_realizacao(body, u['id'], u['username'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': rid})
                return
        if path.startswith('/api/realizacoes/') and path.endswith('/historico'):
            # /api/realizacoes/{colab}/{trein}/historico? handle below differently
            pass
        if path.startswith('/api/realizacoes/'):
            parts = path.split('/')
            # /api/realizacoes/{id}
            if len(parts) == 4 and parts[3].isdigit():
                rid = int(parts[3])
                if method == 'GET':
                    json_resp(self, 200, models.get_realizacao(rid) or {})
                    return
                if method == 'PUT':
                    if not require_perm(self, u, 'realizacoes'): return
                    body = read_body(self)
                    ok, err = models.update_realizacao(rid, body, u['id'], u['username'], body.get('motivo'))
                    if not ok: json_resp(self, 400, {'error': err}); return
                    json_resp(self, 200, {'ok': True})
                    return
                if method == 'DELETE':
                    if not (auth.has_perm(u, 'delete') or auth.has_perm(u, 'pendencias')):
                        json_resp(self, 403, {'error': 'Sem permissão'}); return
                    models.delete_realizacao(rid, u['id'], u['username'])
                    json_resp(self, 200, {'ok': True})
                    return

        # historico realizacoes: /api/historico?colaborador_id=&treinamento_id=
        if path == '/api/historico':
            if method == 'GET':
                cid = int(qs['colaborador_id'][0]); tid = int(qs['treinamento_id'][0])
                json_resp(self, 200, models.historico_realizacoes(cid, tid))
                return

        # ---- dashboard ----
        if path == '/api/dashboard':
            if method == 'GET':
                filtros = {}
                for k in ['ano','mes','setor_id','cargo_id','treinamento_id','colaborador_id','status']:
                    if qs.get(k): filtros[k] = qs[k][0]
                if filtros.get('setor_id'): filtros['setor_id']=int(filtros['setor_id'])
                if filtros.get('cargo_id'): filtros['cargo_id']=int(filtros['cargo_id'])
                if filtros.get('treinamento_id'): filtros['treinamento_id']=int(filtros['treinamento_id'])
                if filtros.get('colaborador_id'): filtros['colaborador_id']=int(filtros['colaborador_id'])
                if qs.get('colab_ativo'): filtros['colab_ativo'] = (qs['colab_ativo'][0]=='1')
                json_resp(self, 200, models.dashboard(filtros))
                return

        # ---- pendencias ----
        if path == '/api/pendencias':
            if method == 'GET':
                regs = models.list_realizacoes({'colab_ativo': True})
                # filter to vencido/proximo/incompleto
                items = [r for r in regs if r['status'] in ('vencido','proximo','dados_incompletos')]
                # attach acomp
                for r in items:
                    a = models.get_acomp(r['id'])
                    r['acomp'] = a
                json_resp(self, 200, items)
                return
        if path == '/api/pendencias/acomp' and method == 'POST':
            if not require_perm(self, u, 'pendencias'): return
            body = read_body(self)
            models.marcar_acompanhada(body['realizacao_id'], body.get('status','acompanhada'), body.get('observacao'), body.get('responsavel'))
            json_resp(self, 200, {'ok': True})
            return

        # ---- relatorios ----
        if path == '/api/relatorio/mensal':
            if method == 'GET':
                ano = qs['ano'][0]; mes = qs['mes'][0].zfill(2)
                regs = models.list_realizacoes({'ano': ano, 'excluir_afastados': True})
                # filter vencimento in that month
                regs = [r for r in regs if r['data_vencimento'] and r['data_vencimento'][5:7]==mes and r['data_vencimento'][:4]==str(ano)]
                # group by day
                import calendar
                y = int(ano); m = int(mes)
                ndays = calendar.monthrange(y, m)[1]
                days = {d: {'vencido':0,'proximo':0,'em_dia':0,'incompleto':0,'total':0} for d in range(1, ndays+1)}
                for r in regs:
                    d = int(r['data_vencimento'][8:10])
                    days[d]['total'] += 1
                    days[d][r['status'] if r['status']!='dados_incompletos' else 'incompleto'] += 1
                json_resp(self, 200, {'ano': ano, 'mes': mes, 'ndays': ndays, 'days': days, 'registros': regs})
                return

        if path == '/api/relatorio/anual':
            if method == 'GET':
                # vencimentos por ano
                regs = models.list_realizacoes({'excluir_afastados': True})
                por_ano = {}
                for r in regs:
                    if r['data_vencimento']:
                        y = r['data_vencimento'][:4]
                        por_ano.setdefault(y, {'ano':y,'total':0,'em_dia':0,'proximo':0,'vencido':0,'incompleto':0})
                        por_ano[y]['total'] += 1
                        st = r['status'] if r['status']!='dados_incompletos' else 'incompleto'
                        por_ano[y][st] += 1
                json_resp(self, 200, sorted(por_ano.values(), key=lambda x: x['ano']))
                return

        # export excel
        if path == '/api/export/excel':
            if method == 'GET':
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = 'Treinamentos'
                headers = ['Colaborador','Cargo','Setor','Treinamento','Data Realização','Prazo (dias)','Data Vencimento','Status','Dias']
                ws.append(headers)
                filtros = {}
                for k in ['ano','mes','setor_id','cargo_id','treinamento_id','colaborador_id','status']:
                    if qs.get(k): filtros[k] = qs[k][0]
                filtros['excluir_afastados'] = True
                regs = models.list_realizacoes(filtros)
                for r in regs:
                    ws.append([r['colaborador_nome'], r.get('cargo_nome'), r.get('setor_nome'), r['treinamento_nome'],
                               r['data_realizacao_fmt'], r['prazo_validade_dias'], r['data_vencimento_fmt'], r['status_label'], r['dias']])
                # save
                outdir = os.path.join(BASE, '..', 'exports')
                os.makedirs(outdir, exist_ok=True)
                fname = f"export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                fpath = os.path.join(outdir, fname)
                wb.save(fpath)
                # serve file
                with open(fpath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        if path == '/api/export/csv':
            if method == 'GET':
                import csv, io
                filtros = {}
                for k in ['ano','mes','setor_id','cargo_id','treinamento_id','colaborador_id','status']:
                    if qs.get(k): filtros[k] = qs[k][0]
                filtros['excluir_afastados'] = True
                regs = models.list_realizacoes(filtros)
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(['Colaborador','Cargo','Setor','Treinamento','Data Realização','Prazo (dias)','Data Vencimento','Status','Dias'])
                for r in regs:
                    w.writerow([r['colaborador_nome'], r.get('cargo_nome'), r.get('setor_nome'), r['treinamento_nome'],
                                r['data_realizacao_fmt'], r['prazo_validade_dias'], r['data_vencimento_fmt'], r['status_label'], r['dias']])
                data = buf.getvalue().encode('utf-8-sig')
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="export.csv"')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        # ---- config ----
        if path == '/api/config':
            if method == 'GET':
                json_resp(self, 200, {'janela_alerta_dias': models.janela_alerta()})
                return
            if method == 'POST':
                if not require_perm(self, u, 'config'): return
                body = read_body(self)
                models.set_janela_alerta(int(body.get('janela_alerta_dias', 30)), u['id'])
                json_resp(self, 200, {'ok': True})
                return

        # ---- audit ----
        if path == '/api/audit':
            if method == 'GET':
                if not require_perm(self, u, 'audit'): return
                json_resp(self, 200, models.list_audit())
                return

        # ---- users ----
        if path == '/api/users':
            if method == 'GET':
                if not require_perm(self, u, 'users'): return
                conn = db.get_conn()
                rows = conn.execute("SELECT id,username,role,nome,colaborador_id,ativo,created_at FROM users ORDER BY username").fetchall()
                conn.close()
                json_resp(self, 200, [db.row_to_dict(r) for r in rows])
                return
            if method == 'POST':
                if not require_perm(self, u, 'users'): return
                body = read_body(self)
                # create user
                import secrets, hashlib
                salt = secrets.token_hex(16)
                pw = body.get('password') or 'mudar123'
                h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex()
                conn = db.get_conn()
                try:
                    conn.execute("INSERT INTO users (username,password_hash,salt,role,nome,ativo,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                                 (body['username'], h, salt, body.get('role','consulta'), body.get('nome'), 1, db.now_iso(), db.now_iso()))
                    conn.commit()
                    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                except Exception as e:
                    conn.close(); json_resp(self, 400, {'error': str(e)}); return
                conn.close()
                json_resp(self, 201, {'id': sid})
                return

        if path.startswith('/api/users/') and method == 'PUT':
            if not require_perm(self, u, 'users'): return
            uid = int(path.split('/')[-1])
            body = read_body(self)
            conn = db.get_conn()
            row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if not row:
                conn.close(); json_resp(self, 404, {'error': 'Não encontrado.'}); return
            sets=[]; params=[]
            if body.get('nome') is not None:
                sets.append('nome=?'); params.append(body['nome'])
            if body.get('role') is not None:
                sets.append('role=?'); params.append(body['role'])
            if body.get('ativo') is not None:
                sets.append('ativo=?'); params.append(1 if body['ativo'] else 0)
            if 'colaborador_id' in body:
                sets.append('colaborador_id=?'); params.append(body.get('colaborador_id'))
            if body.get('password'):
                import hashlib, secrets
                salt = secrets.token_hex(16)
                h = hashlib.pbkdf2_hmac('sha256', body['password'].encode(), salt.encode(), 100000).hex()
                sets.append('password_hash=?'); params.append(h)
                sets.append('salt=?'); params.append(salt)
            if not sets:
                conn.close(); json_resp(self, 400, {'error': 'Nada para atualizar.'}); return
            sets.append('updated_at=?'); params.append(db.now_iso())
            params.append(uid)
            try:
                conn.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", params)
                conn.commit()
            except Exception as e:
                conn.close(); json_resp(self, 400, {'error': str(e)}); return
            conn.close()
            json_resp(self, 200, {'ok': True})
            return

        # ---- meu perfil ----
        if path == '/api/me/profile' and method == 'GET':
            u = require_auth(self)
            if not u: return
            conn = db.get_conn()
            colab = None
            if u.get('colaborador_id'):
                r = conn.execute("""SELECT c.*, s.nome AS setor_nome FROM colaboradores c LEFT JOIN setores s ON s.id=c.setor_id WHERE c.id=?""", (u['colaborador_id'],)).fetchone()
                colab = db.row_to_dict(r) if r else None
            setores = [db.row_to_dict(r) for r in conn.execute("SELECT id,nome FROM setores ORDER BY nome").fetchall()]
            conn.close()
            json_resp(self, 200, {'user': {'id':u['id'],'username':u['username'],'nome':u['nome'],'role':u['role']}, 'colaborador': colab, 'setores': setores})
            return
        if path == '/api/me/profile' and method == 'PUT':
            u = require_auth(self)
            if not u: return
            body = read_body(self)
            conn = db.get_conn()
            # update user nome/password only (never role/permissions)
            usets=[]; uparams=[]
            if body.get('nome') is not None:
                usets.append('nome=?'); uparams.append(body['nome'])
            if body.get('password'):
                import hashlib, secrets
                salt = secrets.token_hex(16)
                h = hashlib.pbkdf2_hmac('sha256', body['password'].encode(), salt.encode(), 100000).hex()
                usets.append('password_hash=?'); uparams.append(h)
                usets.append('salt=?'); uparams.append(salt)
            if usets:
                usets.append('updated_at=?'); uparams.append(db.now_iso())
                uparams.append(u['id'])
                conn.execute(f"UPDATE users SET {','.join(usets)} WHERE id=?", uparams)
            # update linked colaborador nome/setor only
            if u.get('colaborador_id') and body.get('colaborador'):
                cdata = body['colaborador']
                csets=[]; cparams=[]
                if cdata.get('nome') is not None:
                    csets.append('nome=?'); cparams.append(cdata['nome'])
                if 'setor_id' in cdata:
                    csets.append('setor_id=?'); cparams.append(cdata.get('setor_id'))
                if csets:
                    csets.append('updated_at=?'); cparams.append(db.now_iso())
                    cparams.append(u['colaborador_id'])
                    conn.execute(f"UPDATE colaboradores SET {','.join(csets)} WHERE id=?", cparams)
            conn.commit()
            conn.close()
            json_resp(self, 200, {'ok': True})
            return

        # ---- agendamentos ----
        if path == '/api/agendamentos':
            if method == 'GET':
                filtros = {}
                if qs.get('status'): filtros['status'] = qs['status'][0]
                if qs.get('colaborador_id'): filtros['colaborador_id'] = int(qs['colaborador_id'][0])
                json_resp(self, 200, models.list_agendamentos(filtros))
                return
            if method == 'POST':
                if not require_perm(self, u, 'realizacoes'): return
                body = read_body(self)
                sid, err = models.create_agendamento(body, u['id'])
                if err: json_resp(self, 400, {'error': err}); return
                json_resp(self, 201, {'id': sid})
                return
        if path.startswith('/api/agendamentos/') and path.endswith('/realizar'):
            if method == 'POST':
                if not require_perm(self, u, 'realizacoes'): return
                aid = int(path.split('/')[-2])
                body = read_body(self)
                ok, err = models.marcar_agendamento_realizado(aid, body.get('data_realizacao'), u['id'])
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return
        if path.startswith('/api/agendamentos/') and path.endswith('/cancelar'):
            if method == 'POST':
                if not require_perm(self, u, 'realizacoes'): return
                aid = int(path.split('/')[-2])
                ok, err = models.cancelar_agendamento(aid, u['id'])
                if not ok: json_resp(self, 400, {'error': err}); return
                json_resp(self, 200, {'ok': True})
                return

        if path.startswith('/api/agendamentos/') and method == 'DELETE':
            if not require_perm(self, u, 'delete'): return
            aid = int(path.split('/')[-1])
            conn = db.get_conn()
            ag = conn.execute("SELECT * FROM agendamentos WHERE id=?", (aid,)).fetchone()
            if not ag:
                conn.close(); json_resp(self, 404, {'error': 'Não encontrado.'}); return
            if ag['realizacao_id']:
                conn.execute("DELETE FROM pendencias_acomp WHERE realizacao_id=?", (ag['realizacao_id'],))
                conn.execute("DELETE FROM agendamentos WHERE id=?", (aid,))
                conn.execute("DELETE FROM realizacoes WHERE id=?", (ag['realizacao_id'],))
            else:
                conn.execute("DELETE FROM agendamentos WHERE id=?", (aid,))
            conn.commit()
            conn.close()
            json_resp(self, 200, {'ok': True})
            return

        # ---- import ----
        if path == '/api/import/preview' and method == 'POST':
            if not require_perm(self, u, 'import'): return
            body = read_body(self)
            fpath = body.get('file_path')
            if body.get('content_base64'):
                import base64, tempfile
                try:
                    raw = base64.b64decode(body['content_base64'])
                except Exception:
                    json_resp(self, 400, {'error': 'Base64 inválido.'}); return
                fd, fpath = tempfile.mkstemp(suffix='.xlsm', dir=os.path.join(BASE, '..', 'data'))
                with os.fdopen(fd, 'wb') as fh:
                    fh.write(raw)
            if not fpath or not os.path.isfile(fpath):
                json_resp(self, 400, {'error': 'Arquivo não encontrado. Envie file_path ou content_base64.'}); return
            try:
                res = import_xl.preview(fpath)
            except Exception as e:
                json_resp(self, 400, {'error': str(e)}); return
            json_resp(self, 200, res)
            return
        if path == '/api/import/commit' and method == 'POST':
            if not require_perm(self, u, 'import'): return
            body = read_body(self)
            fpath = body.get('file_path')
            if body.get('content_base64'):
                import base64, tempfile
                try:
                    raw = base64.b64decode(body['content_base64'])
                except Exception:
                    json_resp(self, 400, {'error': 'Base64 inválido.'}); return
                fd, fpath = tempfile.mkstemp(suffix='.xlsm', dir=os.path.join(BASE, '..', 'data'))
                with os.fdopen(fd, 'wb') as fh:
                    fh.write(raw)
            if not fpath or not os.path.isfile(fpath):
                json_resp(self, 400, {'error': 'Arquivo não encontrado.'}); return
            try:
                res = import_xl.commit(fpath, u['id'], u['username'])
            except Exception as e:
                json_resp(self, 400, {'error': str(e)}); return
            json_resp(self, 200, res)
            return

        # ---- colaborador treinamentos summary (ficha) already handled ----

        json_resp(self, 404, {'error': 'Rota não encontrada'})

    def do_GET(self):
        self.route('GET')
    def do_POST(self):
        self.route('POST')
    def do_PUT(self):
        self.route('PUT')
    def do_DELETE(self):
        self.route('DELETE')

class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    os.chdir(BASE)
    with ReusableTCPServer(('0.0.0.0', PORT), Handler) as httpd:
        print(f'Server running on port {PORT}')
        httpd.serve_forever()
