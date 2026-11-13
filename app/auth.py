import hashlib, secrets, datetime, db

def hash_password(pw, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex()
    return h, salt

def verify_password(pw, h, salt):
    return hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex() == h

def create_session(user_id, remember=False):
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.now()
    exp = now + datetime.timedelta(days=30 if remember else 7)
    conn = db.get_conn()
    conn.execute("INSERT INTO sessions (user_id,token,created_at,expires_at) VALUES (?,?,?,?)",
                 (user_id, token, now.strftime('%Y-%m-%d %H:%M:%S'), exp.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return token

def get_user_by_token(token):
    if not token:
        return None
    conn = db.get_conn()
    row = conn.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                          WHERE s.token=? AND s.expires_at > ?""", (token, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))).fetchone()
    conn.close()
    return db.row_to_dict(row) if row else None

def delete_session(token):
    conn = db.get_conn()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()

PERMS = {
    'admin': {'users','config','import','delete','audit','all'},
    'rh': {'cadastros','realizacoes','relatorios','export','pendencias'},
    'consulta': {'view','relatorios'},
}

def has_perm(user, perm):
    if not user: return False
    role = user.get('role','consulta')
    if role == 'admin': return True
    return perm in PERMS.get(role, set())
