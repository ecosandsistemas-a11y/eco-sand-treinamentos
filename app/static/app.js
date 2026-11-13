const API = '';
let state = { user: null, route: 'dashboard' };
window.addEventListener('error', (e) => { console.error('JS ERROR:', e.message, e.error); });

async function api(path, opts={}) {
  const token = localStorage.getItem('eco_token');
  const headers = { 'Content-Type': 'application/json', ...(opts.headers||{}) };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const r = await fetch(API + path, {
    credentials: 'include',
    headers,
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  if (r.status === 401) { localStorage.removeItem('eco_token'); state.user = null; render(); throw new Error('unauth'); }
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || 'Erro');
    return j;
  }
  if (!r.ok) throw new Error('Erro ' + r.status);
  return r;
}

function $(sel){ return document.querySelector(sel); }
function el(html){ const d=document.createElement('div'); d.innerHTML=html; return d.firstElementChild; }

function badge(status){ return `<span class="badge ${status}">${statusLabel(status)}</span>`; }
function badgeAtivo(v){ return `<span class="badge ${v?'ativo':'inativo'}">${v?'Ativo':'Inativo'}</span>`; }
function badgeSituacao(v){ const m = v==='afastado'?'afastado':(v==='inativo'?'inativo':'ativo'); const lbl = v==='afastado'?'Afastado':(v==='inativo'?'Inativo':'Ativo'); return `<span class="badge ${m}">${lbl}</span>`; }
function statusLabel(s){
  return {em_dia:'Treinamento em dia', proximo:'Próximo do vencimento', vencido:'Treinamento Vencido', dados_incompletos:'Dados incompletos'}[s] || s;
}

function applyTheme() {
  const dark = localStorage.getItem('eco_theme') === 'dark';
  document.body.classList.toggle('dark', dark);
}
async function init() {
  applyTheme();
  window.addEventListener('hashchange', () => { state.route = location.hash.replace('#','') || 'dashboard'; render(); });
  try {
    const token = localStorage.getItem('eco_token');
    const headers = token ? { 'Authorization': 'Bearer ' + token } : {};
    const r = await fetch(API + '/api/me', { credentials: 'include', headers });
    if (r.ok) { const me = await r.json(); state.user = me.user; }
    else { state.user = null; localStorage.removeItem('eco_token'); }
  } catch(e) { state.user = null; }
  state.route = location.hash.replace('#','') || 'dashboard';
  render();
}

function render() {
  const app = $('#app');
  if (!state.user) { app.innerHTML = loginView(); bindLogin(); return; }
  app.innerHTML = layoutView();
  bindLayout();
  loadRoute();
}

function loginView() {
  return `<div class="login-wrap"><div class="login-card">
    <img src="/static/logo.png" alt="Eco Sand" style="max-width:200px;height:auto;margin-bottom:12px;" />
    <h2>Eco Sand | Gestão de Treinamentos</h2>
    <p style="color:#6b7280;font-size:13px;">Acesse com suas credenciais</p>
    <input id="u" placeholder="Usuário" />
    <input id="p" type="password" placeholder="Senha" />
    <button class="btn primary" style="width:100%" id="btnLogin">Entrar</button>
    <div id="loginErr" style="color:#dc2626;font-size:13px;margin-top:8px;"></div>
    <p style="font-size:11px;color:#6b7280;margin-top:12px;">Padrão: admin / admin123</p>
  </div></div>`;
}
function bindLogin() {
  $('#btnLogin').onclick = async () => {
    try {
      const r = await api('/api/login', { method:'POST', body: { username: $('#u').value, password: $('#p').value } });
      if (r.token) localStorage.setItem('eco_token', r.token);
      state.user = r.user;
      state.route = 'dashboard';
      try { history.replaceState(null, '', '#dashboard'); } catch(e) {}
      render();
    } catch(e) { $('#loginErr').textContent = e.message; }
  };
  $('#p').addEventListener('keydown', e => { if (e.key==='Enter') $('#btnLogin').click(); });
}

function layoutView() {
  const links = [
    ['dashboard','Dashboard'],
    ['colaboradores','Colaboradores'],
    ['setores','Setores'],
    ['cargos','Cargos'],
    ['treinamentos','Treinamentos'],
    ['realizacoes','Realizações'],
    ['agenda','Agenda'],
    ['relatorios','Relatórios'],
    ['pendencias','Pendências'],
    ['importacao','Importação'],
    ['usuarios','Usuários'],
    ['auditoria','Auditoria'],
    ['config','Configurações'],
  ];
  return `<div class="layout">
    <aside class="sidebar" id="sidebar">
      <img src="/static/logo.png" alt="Eco Sand" style="max-width:100%;height:auto;margin-bottom:8px;" />
      <div class="sub">Gestão de Treinamentos</div>
      <nav>${links.map(([r,l])=>`<a href="#${r}" class="${state.route===r?'active':''}">${l}</a>`).join('')}</nav>
      <div class="userbox">${state.user.nome||state.user.username}<br><small>${state.user.role}</small><br><a href="#" id="logout" style="color:#fff;text-decoration:underline;font-size:12px;">Sair</a></div>
    </aside>
    <main class="main">
      <div class="topbar">
        <button class="btn hamburger" id="ham">☰</button>
        <h2 id="pageTitle"></h2>
        <button class="btn" id="themeToggle" title="Alternar tema">🌙/☀️</button>
      </div>
      <div id="content"></div>
    </main>
  </div>
  <div class="modal-backdrop" id="modalBackdrop"><div class="modal" id="modal"></div></div>`;
}
function bindLayout() {
  $('#logout').onclick = async (e) => { e.preventDefault(); await api('/api/logout',{method:'POST'}); localStorage.removeItem('eco_token'); state.user=null; state.route='dashboard'; try { history.replaceState(null,'','#'); } catch(e){} render(); };
  $('#ham').onclick = () => $('#sidebar').classList.toggle('open');
  $('#themeToggle').onclick = () => {
    const dark = !document.body.classList.contains('dark');
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('eco_theme', dark ? 'dark' : 'light');
  };
}

async function loadRoute() {
  const c = $('#content');
  c.innerHTML = '<div class="spinner"></div>';
  try {
    switch(state.route) {
      case 'dashboard': await viewDashboard(c); break;
      case 'colaboradores': await viewColaboradores(c); break;
      case 'setores': await viewSetores(c); break;
      case 'cargos': await viewCargos(c); break;
      case 'treinamentos': await viewTreinamentos(c); break;
      case 'realizacoes': await viewRealizacoes(c); break;
      case 'agenda': await viewAgenda(c); break;
      case 'relatorios': await viewRelatorios(c); break;
      case 'pendencias': await viewPendencias(c); break;
      case 'importacao': await viewImportacao(c); break;
      case 'usuarios': await viewUsuarios(c); break;
      case 'auditoria': await viewAuditoria(c); break;
      case 'config': await viewConfig(c); break;
      default: c.innerHTML = '<div class="empty">Módulo não encontrado</div>';
    }
  } catch(e) {
    c.innerHTML = `<div class="card">Erro: ${e.message}</div>`;
  }
}

// ---------- helpers ----------
function modal(html) {
  $('#modal').innerHTML = html;
  $('#modalBackdrop').style.display = 'flex';
  $('#modalBackdrop').onclick = (e) => { if (e.target.id==='modalBackdrop') closeModal(); };
}
function closeModal() { $('#modalBackdrop').style.display = 'none'; }

async function viewDashboard(c) {
  const f = filtersState.dashboard || {};
  const qs = buildQs(f);
  const d = await api('/api/dashboard?' + qs);
  const kpi = (label,val,cls,sub='') => `<div class="kpi ${cls}"><div class="label">${label}</div><div class="value">${val}</div><div class="sub">${sub}</div></div>`;
  c.innerHTML = `
    <div class="filters">
      <div class="form-group"><label>Ano</label><input id="fAno" value="${f.ano||''}" placeholder="2025"></div>
      <div class="form-group"><label>Mês</label><input id="fMes" value="${f.mes||''}" placeholder="1-12"></div>
      <div class="form-group"><label>Setor</label><select id="fSetor"><option value="">Todos</option></select></div>
      <div class="form-group"><label>Cargo</label><select id="fCargo"><option value="">Todos</option></select></div>
      <div class="form-group"><label>Situação</label><select id="fStatus">
        <option value="">Todas</option>
        <option value="em_dia">Em dia</option><option value="proximo">Próximo</option><option value="vencido">Vencido</option><option value="dados_incompletos">Incompleto</option>
      </select></div>
      <button class="btn" id="btnFiltrar">Filtrar</button>
      <button class="btn" id="btnLimpar">Limpar</button>
    </div>
    <div class="grid cols-4">
      ${kpi('Total de registros', d.total, '', 'treinamentos')}
      ${kpi('Em dia', d.em_dia, 'success', d.pct_dia+'%')}
      ${kpi('Próximos do vencimento', d.proximo, 'warning', '')}
      ${kpi('Vencidos', d.vencido, 'danger', d.pct_vencido+'%')}
    </div>
    <div class="grid cols-4" style="margin-top:12px;">
      ${kpi('Dados incompletos', d.incompleto, '', '')}
      ${kpi('Colaboradores com vencido', d.colabs_vencido, 'danger', '')}
      ${kpi('Colaboradores próx. venc.', d.colabs_proximo, 'warning', '')}
      ${kpi('A vencer em 30 dias', d.prox_30, 'warning', '7d: '+d.prox_7+' | 15d: '+d.prox_15)}
    </div>
    <div class="grid cols-2" style="margin-top:12px;">
      <div class="card">
        <h3>Distribuição por situação</h3>
        ${barChart([['Em dia',d.em_dia],['Próximo',d.proximo],['Vencido',d.vencido],['Incompleto',d.incompleto]])}
      </div>
      <div class="card">
        <h3>Vencimentos por mês</h3>
        ${barChart(d.por_mes.map(x=>[mesNome(x.mes), x.qtd]))}
      </div>
    </div>
    <div class="grid cols-2">
      <div class="card">
        <h3>Situação por setor</h3>
        ${tableSetor(d.por_setor)}
      </div>
      <div class="card">
        <h3>Treinamentos com mais pendências</h3>
        ${tableTreinPend(d.por_trein_pend)}
      </div>
    </div>
    <div class="card">
      <h3>Prioridades (atenção imediata)</h3>
      ${tablePrioridades(d.prioridades)}
    </div>
  `;
  // load setores/cargos into selects
  const setores = await api('/api/setores');
  const cargos = await api('/api/cargos');
  const fs = $('#fSetor'); setores.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.nome;if(f.setor_id==s.id)o.selected=true;fs.appendChild(o);});
  const fc = $('#fCargo'); cargos.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.nome;if(f.cargo_id==s.id)o.selected=true;fc.appendChild(o);});
  if (f.status) $('#fStatus').value = f.status;
  $('#btnFiltrar').onclick = () => {
    filtersState.dashboard = {
      ano: $('#fAno').value, mes: $('#fMes').value,
      setor_id: $('#fSetor').value, cargo_id: $('#fCargo').value, status: $('#fStatus').value
    };
    viewDashboard(c);
  };
  $('#btnLimpar').onclick = () => { filtersState.dashboard = {}; viewDashboard(c); };
}

let filtersState = {};

function buildQs(f) {
  const p = new URLSearchParams();
  for (const k in f) if (f[k]) p.set(k, f[k]);
  return p.toString();
}
function mesNome(m){ return ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][m-1]; }
function barChart(data) {
  const max = Math.max(1, ...data.map(x=>x[1]));
  return data.map(([l,v]) => `<div class="chart-bar"><div class="label">${l}</div><div class="bar" style="width:${Math.round(v/max*200)}px"></div><div class="val">${v}</div></div>`).join('');
}
function tableSetor(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>Setor</th><th>Total</th><th>Em dia</th><th>Próximo</th><th>Vencido</th><th>Incompleto</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td>${r.setor}</td><td>${r.total}</td><td>${r.em_dia}</td><td>${r.proximo}</td><td>${r.vencido}</td><td>${r.incompleto}</td></tr>`).join('')}</tbody></table></div>`;
}
function tableTreinPend(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>Treinamento</th><th>Pendências</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td>${r.treinamento}</td><td>${r.qtd}</td></tr>`).join('')}</tbody></table></div>`;
}
function tablePrioridades(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>Colaborador</th><th>Cargo</th><th>Setor</th><th>Treinamento</th><th>Última realização</th><th>Vencimento</th><th>Dias</th><th>Situação</th></tr></thead><tbody>
    ${rows.map(r=>`<tr>
      <td>${r.colaborador_nome}</td><td>${r.cargo_nome||''}</td><td>${r.setor_nome||''}</td><td>${r.treinamento_nome}</td>
      <td>${r.data_realizacao_fmt}</td><td>${r.data_vencimento_fmt}</td><td>${r.dias}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
}

// ---------- Setores ----------
async function viewSetores(c) {
  const rows = await api('/api/setores');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0">Setores</h3>
        <button class="btn primary" id="btnNovoSetor">Novo setor</button>
      </div>
      <div class="table-wrap" style="margin-top:12px;">
        <table><thead><tr><th>Nome</th><th>Descrição</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
        ${rows.map(r=>`<tr>
          <td>${r.nome}</td><td>${r.descricao||''}</td><td>${badgeAtivo(r.ativo)}</td>
          <td><button class="btn small" onclick="editarSetor(${r.id},'${esc(r.nome)}','${esc(r.descricao||'')}',${r.ativo})">Editar</button></td>
        </tr>`).join('')}
        </tbody></table>
      </div>
    </div>`;
  $('#btnNovoSetor').onclick = () => modalFormSetor();
}
function esc(s){ return String(s).replace(/'/g,'&#39;').replace(/"/g,'&quot;'); }
function modalFormSetor(id=null, nome='', desc='', ativo=1) {
  modal(`<h3>${id?'Editar':'Novo'} setor</h3>
    <div class="form-grid">
      <div class="form-group"><label>Nome</label><input id="sNome" value="${esc(nome)}"></div>
      <div class="form-group"><label>Descrição</label><input id="sDesc" value="${esc(desc)}"></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarSetor">Salvar</button>
    </div>`);
  $('#btnSalvarSetor').onclick = async () => {
    try {
      const body = { nome: $('#sNome').value, descricao: $('#sDesc').value };
      if (id) await api('/api/setores/'+id, {method:'PUT', body});
      else await api('/api/setores', {method:'POST', body});
      closeModal(); viewSetores($('#content'));
    } catch(e){ alert(e.message); }
  };
}
window.editarSetor = (id,nome,desc,ativo) => modalFormSetor(id,nome,desc,ativo);

// ---------- Cargos ----------
async function viewCargos(c) {
  const rows = await api('/api/cargos');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0">Cargos</h3>
        <button class="btn primary" id="btnNovoCargo">Novo cargo</button>
      </div>
      <div class="table-wrap" style="margin-top:12px;">
        <table><thead><tr><th>Nome</th><th>Descrição</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
        ${rows.map(r=>`<tr>
          <td>${r.nome}</td><td>${r.descricao||''}</td><td>${badgeAtivo(r.ativo)}</td>
          <td><button class="btn small" onclick="editarCargo(${r.id},'${esc(r.nome)}','${esc(r.descricao||'')}')">Editar</button></td>
        </tr>`).join('')}
        </tbody></table>
      </div>
    </div>`;
  $('#btnNovoCargo').onclick = () => modalFormCargo();
}
function modalFormCargo(id=null, nome='', desc='') {
  modal(`<h3>${id?'Editar':'Novo'} cargo</h3>
    <div class="form-grid">
      <div class="form-group"><label>Nome</label><input id="cNome" value="${esc(nome)}"></div>
      <div class="form-group"><label>Descrição</label><input id="cDesc" value="${esc(desc)}"></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarCargo">Salvar</button>
    </div>`);
  $('#btnSalvarCargo').onclick = async () => {
    try {
      const body = { nome: $('#cNome').value, descricao: $('#cDesc').value };
      if (id) await api('/api/cargos/'+id, {method:'PUT', body});
      else await api('/api/cargos', {method:'POST', body});
      closeModal(); viewCargos($('#content'));
    } catch(e){ alert(e.message); }
  };
}
window.editarCargo = (id,nome,desc) => modalFormCargo(id,nome,desc);

// ---------- Treinamentos ----------
async function viewTreinamentos(c) {
  const rows = await api('/api/treinamentos');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0">Treinamentos / Cursos</h3>
        <button class="btn primary" id="btnNovoTrein">Novo treinamento</button>
      </div>
      <div class="table-wrap" style="margin-top:12px;">
        <table><thead><tr><th>Nome</th><th>Código</th><th>Categoria</th><th>Prazo (dias)</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
        ${rows.map(r=>`<tr>
          <td>${r.nome}</td><td>${r.codigo||''}</td><td>${r.categoria||''}</td><td>${r.prazo_validade_dias==null?'Sem validade':r.prazo_validade_dias}</td>
          <td>${badgeAtivo(r.ativo)}</td>
          <td><button class="btn small" onclick="editarTrein(${r.id})">Editar</button></td>
        </tr>`).join('')}
        </tbody></table>
      </div>
    </div>`;
  $('#btnNovoTrein').onclick = () => modalFormTrein();
}
function modalFormTrein(id=null, data={}) {
  modal(`<h3>${id?'Editar':'Novo'} treinamento</h3>
    <div class="form-grid">
      <div class="form-group"><label>Nome</label><input id="tNome" value="${esc(data.nome||'')}"></div>
      <div class="form-group"><label>Código</label><input id="tCod" value="${esc(data.codigo||'')}"></div>
      <div class="form-group"><label>Categoria</label><input id="tCat" value="${esc(data.categoria||'')}"></div>
      <div class="form-group"><label>Prazo de validade (dias)</label><input id="tPrazo" type="number" value="${data.prazo_validade_dias==null?'':data.prazo_validade_dias}" placeholder="vazio = sem validade"></div>
      <div class="form-group"><label>Descrição</label><input id="tDesc" value="${esc(data.descricao||'')}"></div>
      <div class="form-group"><label>Observações</label><input id="tObs" value="${esc(data.observacoes||'')}"></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarTrein">Salvar</button>
    </div>`);
  $('#btnSalvarTrein').onclick = async () => {
    try {
      const body = {
        nome: $('#tNome').value, codigo: $('#tCod').value, categoria: $('#tCat').value,
        descricao: $('#tDesc').value, observacoes: $('#tObs').value,
        prazo_validade_dias: $('#tPrazo').value===''? null : parseInt($('#tPrazo').value)
      };
      if (id) await api('/api/treinamentos/'+id, {method:'PUT', body});
      else await api('/api/treinamentos', {method:'POST', body});
      closeModal(); viewTreinamentos($('#content'));
    } catch(e){ alert(e.message); }
  };
}
window.editarTrein = async (id) => {
  const t = await api('/api/treinamentos/'+id);
  modalFormTrein(id, t);
};

// ---------- Colaboradores ----------
async function viewColaboradores(c) {
  const setores = await api('/api/setores');
  const cargos = await api('/api/cargos');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h3 style="margin:0">Colaboradores</h3>
        <button class="btn primary" id="btnNovoColab">Novo colaborador</button>
      </div>
      <div class="filters">
        <div class="form-group"><label>Busca</label><input id="cb" placeholder="nome ou código"></div>
        <div class="form-group"><label>Setor</label><select id="cs"><option value="">Todos</option>${setores.map(s=>`<option value="${s.id}">${s.nome}</option>`).join('')}</select></div>
        <div class="form-group"><label>Cargo</label><select id="cc"><option value="">Todos</option>${cargos.map(s=>`<option value="${s.id}">${s.nome}</option>`).join('')}</select></div>
        <div class="form-group"><label>Situação</label><select id="ca"><option value="">Todas</option><option value="ativo">Ativo</option><option value="inativo">Inativo</option><option value="afastado">Afastado</option></select></div>
        <button class="btn" id="btnFiltrarColab">Filtrar</button>
      </div>
      <div id="colabTable"></div>
    </div>`;
  async function load() {
    const qs = new URLSearchParams();
    if ($('#cb').value) qs.set('busca', $('#cb').value);
    if ($('#cs').value) qs.set('setor_id', $('#cs').value);
    if ($('#cc').value) qs.set('cargo_id', $('#cc').value);
    if ($('#ca').value) qs.set('situacao', $('#ca').value);
    const rows = await api('/api/colaboradores?'+qs.toString());
    $('#colabTable').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Nome</th><th>Código</th><th>Setor</th><th>Cargo</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
      ${rows.map(r=>`<tr>
        <td>${r.nome}</td><td>${r.codigo||''}</td><td>${r.setor_nome||''}</td><td>${r.cargo_nome||''}</td><td>${badgeSituacao(r.situacao|| (r.ativo?'ativo':'inativo'))}</td>
        <td>
          <button class="btn small" onclick="abrirFicha(${r.id})">Ficha</button>
          <button class="btn small" onclick="editarColab(${r.id})">Editar</button>
        </td>
      </tr>`).join('')}</tbody></table></div>`;
  }
  $('#btnFiltrarColab').onclick = load;
  await load();
  $('#btnNovoColab').onclick = () => modalFormColab();
}
async function modalFormColab(id=null, data={}) {
  const setores = await api('/api/setores');
  const cargos = await api('/api/cargos');
  modal(`<h3>${id?'Editar':'Novo'} colaborador</h3>
    <div class="form-grid">
      <div class="form-group"><label>Nome completo</label><input id="clNome" value="${esc(data.nome||'')}"></div>
      <div class="form-group"><label>Código interno</label><input id="clCod" value="${esc(data.codigo||'')}"></div>
      <div class="form-group"><label>Setor</label><select id="clSetor"><option value="">--</option>${setores.map(s=>`<option value="${s.id}" ${data.setor_id==s.id?'selected':''}>${s.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Cargo</label><select id="clCargo"><option value="">--</option>${cargos.map(s=>`<option value="${s.id}" ${data.cargo_id==s.id?'selected':''}>${s.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Matrícula</label><input id="clMat" value="${esc(data.matricula||'')}"></div>
      <div class="form-group"><label>Data admissão</label><input id="clAdm" value="${data.data_admissao||''}" placeholder="AAAA-MM-DD"></div>
      <div class="form-group"><label>Observações</label><input id="clObs" value="${esc(data.observacoes||'')}"></div>
      <div class="form-group"><label>Situação</label><select id="clSituacao"><option value="ativo" ${(data.situacao|| (data.ativo!==0?'ativo':'inativo'))==='ativo'?'selected':''}>Ativo</option><option value="inativo" ${(data.situacao|| (data.ativo!==0?'ativo':'inativo'))==='inativo'?'selected':''}>Inativo</option><option value="afastado" ${(data.situacao)==='afastado'?'selected':''}>Afastado</option></select></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarColab">Salvar</button>
    </div>`);
  $('#btnSalvarColab').onclick = async () => {
    try {
      const body = {
        nome: $('#clNome').value, codigo: $('#clCod').value,
        setor_id: $('#clSetor').value? parseInt($('#clSetor').value): null,
        cargo_id: $('#clCargo').value? parseInt($('#clCargo').value): null,
        matricula: $('#clMat').value, data_admissao: $('#clAdm').value || null,
        observacoes: $('#clObs').value, situacao: $('#clSituacao').value, ativo: $('#clSituacao').value==='ativo'
      };
      if (id) await api('/api/colaboradores/'+id, {method:'PUT', body});
      else await api('/api/colaboradores', {method:'POST', body});
      closeModal(); viewColaboradores($('#content'));
    } catch(e){ alert(e.message); }
  };
}
window.editarColab = async (id) => {
  const c = await api('/api/colaboradores/'+id);
  modalFormColab(id, c);
};

async function abrirFicha(id) {
  const r = await api('/api/colaboradores/'+id+'/ficha');
  const c = r.colaborador;
  const regs = r.realizacoes;
  const total = regs.length;
  const emdia = regs.filter(x=>x.status==='em_dia').length;
  const prox = regs.filter(x=>x.status==='proximo').length;
  const venc = regs.filter(x=>x.status==='vencido').length;
  const inc = regs.filter(x=>x.status==='dados_incompletos').length;
  modal(`<h3>Ficha do colaborador</h3>
    <p><strong>${c.nome}</strong><br>Código: ${c.codigo||'-'} | Cargo: ${c.cargo_nome||'-'} | Setor: ${c.setor_nome||'-'} | Situação: ${badgeSituacao(c.situacao|| (c.ativo?'ativo':'inativo'))}</p>
    <div class="grid cols-4">
      <div class="kpi"><div class="label">Total</div><div class="value">${total}</div></div>
      <div class="kpi success"><div class="label">Em dia</div><div class="value">${emdia}</div></div>
      <div class="kpi warning"><div class="label">Próximo</div><div class="value">${prox}</div></div>
      <div class="kpi danger"><div class="label">Vencido</div><div class="value">${venc}</div></div>
    </div>
    <div class="table-wrap" style="margin-top:12px;">
      <table><thead><tr><th>Treinamento</th><th>Última realização</th><th>Validade (dias)</th><th>Vencimento</th><th>Dias</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
      ${regs.map(r=>`<tr>
        <td>${r.treinamento_nome}</td><td>${r.data_realizacao_fmt}</td><td>${r.prazo_validade_dias==null?'-':r.prazo_validade_dias}</td>
        <td>${r.data_vencimento_fmt||'-'}</td><td>${r.dias==null?'-':r.dias}</td><td>${badge(r.status)}</td>
        <td>
          <button class="btn small" onclick="verHistorico(${c.id},${r.treinamento_id})">Histórico</button>
          <button class="btn small" onclick="registrarRealizacao(${c.id},${r.treinamento_id})">Renovar</button>
        </td>
      </tr>`).join('')}
      </tbody></table>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="registrarRealizacao(${c.id})">Registrar treinamento</button>
      <button class="btn primary" onclick="closeModal()">Fechar</button>
    </div>`);
}

// ---------- Realizacoes ----------
async function viewRealizacoes(c) {
  const setores = await api('/api/setores');
  const cargos = await api('/api/cargos');
  const treins = await api('/api/treinamentos');
  const colabs = await api('/api/colaboradores');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <h3 style="margin:0">Realizações de treinamento</h3>
        <button class="btn primary" id="btnNovaReal">Nova realização</button>
      </div>
      <div class="filters">
        <div class="form-group"><label>Colaborador</label><select id="rfColab"><option value="">Todos</option>${colabs.map(x=>`<option value="${x.id}">${x.nome}</option>`).join('')}</select></div>
        <div class="form-group"><label>Treinamento</label><select id="rfTrein"><option value="">Todos</option>${treins.map(x=>`<option value="${x.id}">${x.nome}</option>`).join('')}</select></div>
        <div class="form-group"><label>Setor</label><select id="rfSetor"><option value="">Todos</option>${setores.map(x=>`<option value="${x.id}">${x.nome}</option>`).join('')}</select></div>
        <div class="form-group"><label>Situação</label><select id="rfStatus"><option value="">Todas</option><option value="em_dia">Em dia</option><option value="proximo">Próximo</option><option value="vencido">Vencido</option><option value="dados_incompletos">Incompleto</option></select></div>
        <div class="form-group"><label>Ano venc.</label><input id="rfAno" placeholder="2025"></div>
        <button class="btn" id="btnFiltrarReal">Filtrar</button>
        <button class="btn" id="btnExportXls">Exportar Excel</button>
        <button class="btn" id="btnExportCsv">Exportar CSV</button>
      </div>
      <div id="realTable"></div>
    </div>`;
  async function load() {
    const qs = new URLSearchParams();
    if ($('#rfColab').value) qs.set('colaborador_id', $('#rfColab').value);
    if ($('#rfTrein').value) qs.set('treinamento_id', $('#rfTrein').value);
    if ($('#rfSetor').value) qs.set('setor_id', $('#rfSetor').value);
    if ($('#rfStatus').value) qs.set('status', $('#rfStatus').value);
    if ($('#rfAno').value) qs.set('ano', $('#rfAno').value);
    const rows = await api('/api/realizacoes?'+qs.toString());
    $('#realTable').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Colaborador</th><th>Treinamento</th><th>Setor</th><th>Última realização</th><th>Prazo</th><th>Vencimento</th><th>Dias</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
      ${rows.map(r=>`<tr>
        <td>${r.colaborador_nome}</td><td>${r.treinamento_nome}</td><td>${r.setor_nome||''}</td>
        <td>${r.data_realizacao_fmt}</td><td>${r.prazo_validade_dias==null?'-':r.prazo_validade_dias}</td>
        <td>${r.data_vencimento_fmt||'-'}</td><td>${r.dias==null?'-':r.dias}</td><td>${badge(r.status)}</td>
        <td>
          <button class="btn small" onclick="editarReal(${r.id})">Editar</button>
          <button class="btn small" onclick="verHistorico(${r.colaborador_id},${r.treinamento_id})">Hist.</button>
        </td>
      </tr>`).join('')}</tbody></table></div>
      <div style="margin-top:8px;color:#6b7280;font-size:12px;">Total: ${rows.length}</div>`;
  }
  $('#btnFiltrarReal').onclick = load;
  $('#btnExportXls').onclick = () => { window.location = '/api/export/excel?' + new URLSearchParams({status:$('#rfStatus').value, ano:$('#rfAno').value}).toString(); };
  $('#btnExportCsv').onclick = () => { window.location = '/api/export/csv'; };
  $('#btnNovaReal').onclick = () => modalFormReal();
  await load();
}

async function modalFormReal(id=null, data={}) {
  const colabs = await api('/api/colaboradores');
  const treins = await api('/api/treinamentos');
  modal(`<h3>${id?'Editar':'Nova'} realização</h3>
    <div class="form-grid">
      <div class="form-group"><label>Colaborador</label><select id="rColab">${colabs.map(x=>`<option value="${x.id}" ${data.colaborador_id==x.id?'selected':''}>${x.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Treinamento</label><select id="rTrein">${treins.map(x=>`<option value="${x.id}" ${data.treinamento_id==x.id?'selected':''}>${x.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Data da realização</label><input id="rData" value="${data.data_realizacao||''}" placeholder="AAAA-MM-DD"></div>
      <div class="form-group"><label>Prazo de validade (dias)</label><input id="rPrazo" type="number" value="${data.prazo_validade_dias==null?'':data.prazo_validade_dias}" placeholder="vazio = usar padrão do treinamento"></div>
      <div class="form-group"><label>Observações</label><input id="rObs" value="${esc(data.observacoes||'')}"></div>
      <div class="form-group"><label>Motivo (se correção)</label><input id="rMotivo" value=""></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarReal">Salvar</button>
    </div>`);
  $('#btnSalvarReal').onclick = async () => {
    try {
      const body = {
        colaborador_id: parseInt($('#rColab').value),
        treinamento_id: parseInt($('#rTrein').value),
        data_realizacao: $('#rData').value,
        prazo_validade_dias: $('#rPrazo').value===''? null : parseInt($('#rPrazo').value),
        observacoes: $('#rObs').value,
        motivo: $('#rMotivo').value
      };
      if (id) await api('/api/realizacoes/'+id, {method:'PUT', body});
      else await api('/api/realizacoes', {method:'POST', body});
      closeModal(); viewRealizacoes($('#content'));
    } catch(e){ alert(e.message); }
  };
}
window.registrarRealizacao = async (colabId, treinId=null) => {
  const colabs = await api('/api/colaboradores');
  const treins = await api('/api/treinamentos');
  modal(`<h3>Registrar realização / renovação</h3>
    <div class="form-grid">
      <div class="form-group"><label>Colaborador</label><select id="rColab">${colabs.map(x=>`<option value="${x.id}" ${colabId==x.id?'selected':''}>${x.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Treinamento</label><select id="rTrein">${treins.map(x=>`<option value="${x.id}" ${treinId==x.id?'selected':''}>${x.nome}</option>`).join('')}</select></div>
      <div class="form-group"><label>Data da realização</label><input id="rData" placeholder="AAAA-MM-DD" value="${new Date().toISOString().slice(0,10)}"></div>
      <div class="form-group"><label>Prazo de validade (dias)</label><input id="rPrazo" type="number" placeholder="vazio = padrão"></div>
      <div class="form-group"><label>Observações</label><input id="rObs"></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarReal2">Salvar</button>
    </div>`);
  $('#btnSalvarReal2').onclick = async () => {
    try {
      const body = {
        colaborador_id: parseInt($('#rColab').value),
        treinamento_id: parseInt($('#rTrein').value),
        data_realizacao: $('#rData').value,
        prazo_validade_dias: $('#rPrazo').value===''? null : parseInt($('#rPrazo').value),
        observacoes: $('#rObs').value
      };
      await api('/api/realizacoes', {method:'POST', body});
      closeModal(); 
      if (state.route==='colaboradores') viewColaboradores($('#content'));
      else viewRealizacoes($('#content'));
    } catch(e){ alert(e.message); }
  };
};
window.editarReal = async (id) => {
  const r = await api('/api/realizacoes/'+id);
  modalFormReal(id, r);
};
window.verHistorico = async (colabId, treinId) => {
  const rows = await api('/api/historico?colaborador_id='+colabId+'&treinamento_id='+treinId);
  modal(`<h3>Histórico de realizações</h3>
    <div class="table-wrap"><table><thead><tr><th>Data realização</th><th>Prazo</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.data_realizacao_fmt}</td><td>${r.prazo_validade_dias==null?'-':r.prazo_validade_dias}</td><td>${r.data_vencimento_fmt||'-'}</td><td>${badge(r.status)}</td></tr>`).join('')}
    </tbody></table></div>
    <div style="margin-top:12px;text-align:right;"><button class="btn primary" onclick="closeModal()">Fechar</button></div>`);
};

// ---------- Agenda ----------
async function viewAgenda(c) {
  const rows = await api('/api/realizacoes');
  c.innerHTML = `
    <div class="card">
      <h3>Agenda de vencimentos</h3>
      <div class="filters">
        <div class="form-group"><label>Filtro rápido</label><select id="agFiltro">
          <option value="todos">Todos</option>
          <option value="vencidos">Vencidos</option>
          <option value="hoje">Vencendo hoje</option>
          <option value="7">Próximos 7 dias</option>
          <option value="15">Próximos 15 dias</option>
          <option value="30">Próximos 30 dias</option>
          <option value="60">Próximos 60 dias</option>
          <option value="90">Próximos 90 dias</option>
        </select></div>
        <button class="btn" id="agAplicar">Aplicar</button>
      </div>
      <div id="agTable"></div>
    </div>`;
  function renderTable(list) {
    $('#agTable').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Colaborador</th><th>Setor</th><th>Treinamento</th><th>Realização</th><th>Vencimento</th><th>Dias</th><th>Situação</th></tr></thead><tbody>
      ${list.map(r=>`<tr><td>${r.colaborador_nome}</td><td>${r.setor_nome||''}</td><td>${r.treinamento_nome}</td><td>${r.data_realizacao_fmt}</td><td>${r.data_vencimento_fmt||'-'}</td><td>${r.dias==null?'-':r.dias}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function apply() {
    const v = $('#agFiltro').value;
    const hoje = new Date();
    let list = rows;
    if (v==='vencidos') list = rows.filter(r=>r.status==='vencido');
    else if (v==='hoje') list = rows.filter(r=>r.dias===0);
    else if (['7','15','30','60','90'].includes(v)) {
      const n = parseInt(v);
      list = rows.filter(r=>r.dias!==null && r.dias>=0 && r.dias<=n);
    }
    renderTable(list);
  }
  $('#agAplicar').onclick = apply;
  renderTable(rows);
}

// ---------- Relatorios ----------
async function viewRelatorios(c) {
  c.innerHTML = `
    <div class="card">
      <h3>Relatórios</h3>
      <div class="filters">
        <button class="btn" onclick="relGeral()">Geral por ano</button>
        <button class="btn" onclick="relTreinamento()">Por treinamento</button>
        <button class="btn" onclick="relColaborador()">Por colaborador</button>
        <button class="btn" onclick="relSetor()">Por setor</button>
        <button class="btn" onclick="relMensal()">Mensal</button>
        <button class="btn" onclick="relAnual()">Anual</button>
        <button class="btn" onclick="relIndividual()">Individual (impressão)</button>
      </div>
      <div id="relContent"></div>
    </div>`;
}
async function relGeral() {
  const ano = prompt('Ano:', new Date().getFullYear());
  if (!ano) return;
  const rows = await api('/api/realizacoes?ano='+ano);
  const total = rows.length;
  const emdia = rows.filter(r=>r.status==='em_dia').length;
  const prox = rows.filter(r=>r.status==='proximo').length;
  const venc = rows.filter(r=>r.status==='vencido').length;
  const inc = rows.filter(r=>r.status==='dados_incompletos').length;
  $('#relContent').innerHTML = `<h4>Relatório geral por ano - ${ano}</h4>
    <div class="grid cols-4">
      <div class="kpi"><div class="label">Total</div><div class="value">${total}</div></div>
      <div class="kpi success"><div class="label">Em dia</div><div class="value">${emdia}</div></div>
      <div class="kpi warning"><div class="label">Próximo</div><div class="value">${prox}</div></div>
      <div class="kpi danger"><div class="label">Vencido</div><div class="value">${venc}</div></div>
    </div>
    <div class="table-wrap" style="margin-top:12px;"><table><thead><tr><th>Colaborador</th><th>Treinamento</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.colaborador_nome}</td><td>${r.treinamento_nome}</td><td>${r.data_vencimento_fmt||'-'}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function relTreinamento() {
  const treins = await api('/api/treinamentos');
  const id = prompt('ID do treinamento:\n' + treins.map(t=>t.id+' - '+t.nome).join('\n'));
  if (!id) return;
  const rows = await api('/api/realizacoes?treinamento_id='+id);
  const t = treins.find(x=>x.id==id);
  const total = rows.length;
  const emdia = rows.filter(r=>r.status==='em_dia').length;
  const prox = rows.filter(r=>r.status==='proximo').length;
  const venc = rows.filter(r=>r.status==='vencido').length;
  const inc = rows.filter(r=>r.status==='dados_incompletos').length;
  $('#relContent').innerHTML = `<h4>Relatório por treinamento - ${t?t.nome:id}</h4>
    <div class="grid cols-4">
      <div class="kpi"><div class="label">Total</div><div class="value">${total}</div></div>
      <div class="kpi success"><div class="label">Em dia</div><div class="value">${emdia}</div></div>
      <div class="kpi warning"><div class="label">Próximo</div><div class="value">${prox}</div></div>
      <div class="kpi danger"><div class="label">Vencido</div><div class="value">${venc}</div></div>
    </div>
    <div class="table-wrap" style="margin-top:12px;"><table><thead><tr><th>Colaborador</th><th>Setor</th><th>Cargo</th><th>Última realização</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.colaborador_nome}</td><td>${r.setor_nome||''}</td><td>${r.cargo_nome||''}</td><td>${r.data_realizacao_fmt}</td><td>${r.data_vencimento_fmt||'-'}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function relColaborador() {
  const colabs = await api('/api/colaboradores');
  const id = prompt('ID do colaborador:\n' + colabs.map(c=>c.id+' - '+c.nome).join('\n'));
  if (!id) return;
  const r = await api('/api/colaboradores/'+id+'/ficha');
  const c = r.colaborador; const regs = r.realizacoes;
  $('#relContent').innerHTML = `<h4>Relatório por colaborador - ${c.nome}</h4>
    <p>Código: ${c.codigo||'-'} | Cargo: ${c.cargo_nome||'-'} | Setor: ${c.setor_nome||'-'}</p>
    <div class="table-wrap"><table><thead><tr><th>Treinamento</th><th>Última realização</th><th>Prazo</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
      ${regs.map(x=>`<tr><td>${x.treinamento_nome}</td><td>${x.data_realizacao_fmt}</td><td>${x.prazo_validade_dias==null?'-':x.prazo_validade_dias}</td><td>${x.data_vencimento_fmt||'-'}</td><td>${badge(x.status)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function relSetor() {
  const setores = await api('/api/setores');
  const id = prompt('ID do setor:\n' + setores.map(s=>s.id+' - '+s.nome).join('\n'));
  if (!id) return;
  const rows = await api('/api/realizacoes?setor_id='+id);
  const s = setores.find(x=>x.id==id);
  const total = rows.length;
  const emdia = rows.filter(r=>r.status==='em_dia').length;
  const prox = rows.filter(r=>r.status==='proximo').length;
  const venc = rows.filter(r=>r.status==='vencido').length;
  const inc = rows.filter(r=>r.status==='dados_incompletos').length;
  const colabs = new Set(rows.map(r=>r.colaborador_id)).size;
  $('#relContent').innerHTML = `<h4>Relatório por setor - ${s?s.nome:id}</h4>
    <div class="grid cols-4">
      <div class="kpi"><div class="label">Colaboradores</div><div class="value">${colabs}</div></div>
      <div class="kpi"><div class="label">Total registros</div><div class="value">${total}</div></div>
      <div class="kpi success"><div class="label">Em dia</div><div class="value">${emdia}</div></div>
      <div class="kpi danger"><div class="label">Vencido</div><div class="value">${venc}</div></div>
    </div>
    <div class="table-wrap" style="margin-top:12px;"><table><thead><tr><th>Colaborador</th><th>Treinamento</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.colaborador_nome}</td><td>${r.treinamento_nome}</td><td>${r.data_vencimento_fmt||'-'}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function relMensal() {
  const ano = prompt('Ano:', new Date().getFullYear());
  const mes = prompt('Mês (1-12):', new Date().getMonth()+1);
  if (!ano||!mes) return;
  const d = await api('/api/relatorio/mensal?ano='+ano+'&mes='+mes);
  let html = `<h4>Relatório mensal - ${mes}/${ano}</h4><div class="calendar-grid">`;
  const weekdays = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
  // header
  html += weekdays.map(w=>`<div style="font-weight:600;text-align:center;">${w}</div>`).join('');
  // first day weekday
  const first = new Date(parseInt(ano), parseInt(mes)-1, 1);
  const startWeekday = first.getDay();
  for (let i=0;i<startWeekday;i++) html += `<div></div>`;
  for (let day=1; day<=d.ndays; day++) {
    const info = d.days[day];
    const cls = info.total>0 ? 'has' : '';
    html += `<div class="calendar-day ${cls}"><div class="dnum">${day}</div><div>${info.total>0? 'Total: '+info.total : ''}</div>
      ${info.vencido? '<div style="color:#dc2626">Venc: '+info.vencido+'</div>':''}
      ${info.proximo? '<div style="color:#d97706">Próx: '+info.proximo+'</div>':''}
    </div>`;
  }
  html += `</div>`;
  // list
  html += `<div class="table-wrap" style="margin-top:12px;"><table><thead><tr><th>Colaborador</th><th>Treinamento</th><th>Vencimento</th><th>Situação</th></tr></thead><tbody>
    ${d.registros.map(r=>`<tr><td>${r.colaborador_nome}</td><td>${r.treinamento_nome}</td><td>${r.data_vencimento_fmt}</td><td>${badge(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
  $('#relContent').innerHTML = html;
}
async function relAnual() {
  const rows = await api('/api/relatorio/anual');
  $('#relContent').innerHTML = `<h4>Relatório anual de vencimentos</h4>
    <div class="table-wrap"><table><thead><tr><th>Ano</th><th>Total</th><th>Em dia</th><th>Próximo</th><th>Vencido</th><th>Incompleto</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.ano}</td><td>${r.total}</td><td>${r.em_dia}</td><td>${r.proximo}</td><td>${r.vencido}</td><td>${r.incompleto}</td></tr>`).join('')}</tbody></table></div>`;
}
async function relIndividual() {
  const colabs = await api('/api/colaboradores');
  const id = prompt('ID do colaborador:\n' + colabs.map(c=>c.id+' - '+c.nome).join('\n'));
  if (!id) return;
  const r = await api('/api/colaboradores/'+id+'/ficha');
  const c = r.colaborador; const regs = r.realizacoes;
  const w = window.open('', '_blank');
  w.document.write(`<!DOCTYPE html><html><head><title>Relatório Individual</title>
    <style>body{font-family:Arial,sans-serif;padding:20px;} table{width:100%;border-collapse:collapse;font-size:12px;} th,td{border:1px solid #ccc;padding:6px;} th{background:#eee;} .header{text-align:center;margin-bottom:20px;} </style></head><body>
    <div class="header"><img src="/static/logo.png" alt="Eco Sand" style="max-height:60px;margin-bottom:8px;" /><h3>Relatório Individual de Treinamentos</h3><p>Data de emissão: ${new Date().toLocaleDateString('pt-BR')}</p></div>
    <p><strong>Nome:</strong> ${c.nome}<br><strong>Código:</strong> ${c.codigo||'-'}<br><strong>Cargo:</strong> ${c.cargo_nome||'-'}<br><strong>Setor:</strong> ${c.setor_nome||'-'}</p>
    <table><thead><tr><th>Treinamento</th><th>Data realização</th><th>Prazo (dias)</th><th>Data vencimento</th><th>Situação</th></tr></thead><tbody>
      ${regs.map(x=>`<tr><td>${x.treinamento_nome}</td><td>${x.data_realizacao_fmt}</td><td>${x.prazo_validade_dias==null?'-':x.prazo_validade_dias}</td><td>${x.data_vencimento_fmt||'-'}</td><td>${statusLabel(x.status)}</td></tr>`).join('')}
    </tbody></table>
    <br><br><p>Assinatura: __________________________</p>
    </body></html>`);
  w.document.close();
  w.print();
}

// ---------- Pendencias ----------
async function viewPendencias(c) {
  const rows = await api('/api/pendencias');
  c.innerHTML = `
    <div class="card">
      <h3>Central de pendências</h3>
      <div class="table-wrap"><table><thead><tr><th>Colaborador</th><th>Treinamento</th><th>Situação</th><th>Vencimento</th><th>Dias</th><th>Acompanhamento</th><th>Ações</th></tr></thead><tbody>
      ${rows.map(r=>`<tr>
        <td>${r.colaborador_nome}</td><td>${r.treinamento_nome}</td><td>${badge(r.status)}</td>
        <td>${r.data_vencimento_fmt||'-'}</td><td>${r.dias==null?'-':r.dias}</td>
        <td>${r.acomp? r.acomp.status_acomp : 'pendente'}</td>
        <td><button class="btn small" onclick="acompanhar(${r.id})">Acompanhar</button></td>
      </tr>`).join('')}</tbody></table></div>
    </div>`;
}
window.acompanhar = (rid) => {
  modal(`<h3>Acompanhar pendência</h3>
    <div class="form-group"><label>Status</label><select id="acStatus"><option value="pendente">Pendente</option><option value="em_acompanhamento">Em acompanhamento</option><option value="resolvido">Resolvido</option></select></div>
    <div class="form-group"><label>Observação</label><textarea id="acObs"></textarea></div>
    <div class="form-group"><label>Responsável</label><input id="acResp"></div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarAcomp">Salvar</button>
    </div>`);
  $('#btnSalvarAcomp').onclick = async () => {
    try {
      await api('/api/pendencias/acomp', {method:'POST', body: {
        realizacao_id: rid, status: $('#acStatus').value, observacao: $('#acObs').value, responsavel: $('#acResp').value
      }});
      closeModal(); viewPendencias($('#content'));
    } catch(e){ alert(e.message); }
  };
};

// ---------- Importacao ----------
async function viewImportacao(c) {
  c.innerHTML = `
    <div class="card">
      <h3>Importação de dados (Excel)</h3>
      <p>Selecione o arquivo .xlsm da planilha original para importar.</p>
      <div class="form-group"><label>Arquivo .xlsm</label><input type="file" id="impFile" accept=".xlsm,.xlsx"></div>
      <div style="margin-top:8px;">
        <button class="btn" id="btnPreview">Pré-visualizar</button>
        <button class="btn primary" id="btnCommit" disabled>Confirmar importação</button>
      </div>
      <div id="impPreview" style="margin-top:12px;"></div>
    </div>`;
  let fileBase64 = null;
  $('#impFile').addEventListener('change', (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => { fileBase64 = reader.result.split(',')[1]; };
    reader.readAsDataURL(f);
  });
  $('#btnPreview').onclick = async () => {
    if (!fileBase64) { alert('Selecione um arquivo primeiro.'); return; }
    try {
      const r = await api('/api/import/preview', {method:'POST', body: { content_base64: fileBase64 }});
      $('#impPreview').innerHTML = `<div class="card">
        <p><strong>Totais:</strong> setores ${r.totais.setores}, cargos ${r.totais.cargos}, treinamentos ${r.totais.treinamentos}, colaboradores ${r.totais.colaboradores}, lançamentos ${r.totais.lancamentos}</p>
        <p><strong>Avisos:</strong> ${r.warnings_count}</p>
        <ul>${r.warnings.map(w=>`<li>${w}</li>`).join('')}</ul>
      </div>`;
      $('#btnCommit').disabled = false;
    } catch(e){ alert(e.message); }
  };
  $('#btnCommit').onclick = async () => {
    if (!confirm('Confirmar importação?')) return;
    try {
      const r = await api('/api/import/commit', {method:'POST', body: { content_base64: fileBase64 }});
      alert('Importação concluída. Importados: '+r.importados+' | Ignorados: '+r.ignorados);
      $('#btnCommit').disabled = true;
    } catch(e){ alert(e.message); }
  };
}

// ---------- Usuarios ----------
async function viewUsuarios(c) {
  const rows = await api('/api/users');
  c.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3 style="margin:0">Usuários</h3>
        <button class="btn primary" id="btnNovoUser">Novo usuário</button>
      </div>
      <div class="table-wrap" style="margin-top:12px;">
        <table><thead><tr><th>Usuário</th><th>Nome</th><th>Perfil</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
        ${rows.map(r=>`<tr><td>${r.username}</td><td>${r.nome||''}</td><td>${r.role}</td><td>${badgeAtivo(r.ativo)}</td><td><button class="btn small" onclick="editarUser(${r.id},'${esc(r.username)}','${esc(r.nome||'')}', '${r.role}', ${r.ativo})">Editar</button></td></tr>`).join('')}</tbody></table>
      </div>
    </div>`;
  $('#btnNovoUser').onclick = () => {
    modal(`<h3>Novo usuário</h3>
      <div class="form-grid">
        <div class="form-group"><label>Usuário</label><input id="uUser"></div>
        <div class="form-group"><label>Nome</label><input id="uNome"></div>
        <div class="form-group"><label>Perfil</label><select id="uRole"><option value="admin">Admin</option><option value="rh">RH</option><option value="consulta">Consulta</option></select></div>
        <div class="form-group"><label>Senha</label><input id="uPass" value="mudar123"></div>
      </div>
      <div style="margin-top:12px;text-align:right;">
        <button class="btn" onclick="closeModal()">Cancelar</button>
        <button class="btn primary" id="btnSalvarUser">Salvar</button>
      </div>`);
    $('#btnSalvarUser').onclick = async () => {
      try {
        await api('/api/users', {method:'POST', body: {
          username: $('#uUser').value, nome: $('#uNome').value, role: $('#uRole').value, password: $('#uPass').value
        }});
        closeModal(); viewUsuarios($('#content'));
      } catch(e){ alert(e.message); }
    };
  };
}

// ---------- Auditoria ----------
async function viewAuditoria(c) {
  const rows = await api('/api/audit');
  c.innerHTML = `
    <div class="card">
      <h3>Histórico de auditoria</h3>
      <div class="table-wrap"><table><thead><tr><th>Data/hora</th><th>Usuário</th><th>Operação</th><th>Entidade</th><th>Registro</th><th>Campo</th><th>Anterior</th><th>Novo</th></tr></thead><tbody>
      ${rows.map(r=>`<tr><td>${r.data_hora}</td><td>${r.username||''}</td><td>${r.tipo_operacao}</td><td>${r.entidade}</td><td>${r.registro_id||''}</td><td>${r.campo||''}</td><td>${r.valor_anterior||''}</td><td>${r.valor_novo||''}</td></tr>`).join('')}</tbody></table></div>
    </div>`;
}

// ---------- Config ----------
async function viewConfig(c) {
  const d = await api('/api/config');
  c.innerHTML = `
    <div class="card">
      <h3>Configurações</h3>
      <div class="form-group"><label>Janela de alerta (dias)</label><input id="cfgJanela" type="number" value="${d.janela_alerta_dias}"></div>
      <div style="margin-top:12px;"><button class="btn primary" id="btnSalvarCfg">Salvar</button></div>
    </div>`;
  $('#btnSalvarCfg').onclick = async () => {
    try {
      await api('/api/config', {method:'POST', body: { janela_alerta_dias: parseInt($('#cfgJanela').value) }});
      alert('Salvo');
    } catch(e){ alert(e.message); }
  };
}

init();


window.editarUser = async (id, username, nome, role, ativo) => {
  modal(`<h3>Editar usuário: ${esc(username)}</h3>
    <div class="form-grid">
      <div class="form-group"><label>Nome</label><input id="eUNome" value="${esc(nome)}"></div>
      <div class="form-group"><label>Perfil (permissões)</label><select id="eURole">
        <option value="admin" ${role==='admin'?'selected':''}>Admin (tudo)</option>
        <option value="rh" ${role==='rh'?'selected':''}>RH (cadastros, realizações, relatórios, export, pendências)</option>
        <option value="consulta" ${role==='consulta'?'selected':''}>Consulta (visualização e relatórios)</option>
      </select></div>
      <div class="form-group"><label>Situação</label><select id="eUAtivo">
        <option value="1" ${ativo!==0?'selected':''}>Ativo</option>
        <option value="0" ${ativo===0?'selected':''}>Inativo</option>
      </select></div>
      <div class="form-group"><label>Nova senha (deixe em branco para manter)</label><input id="eUPass" type="password"></div>
    </div>
    <div style="margin-top:12px;text-align:right;">
      <button class="btn" onclick="closeModal()">Cancelar</button>
      <button class="btn primary" id="btnSalvarEditUser">Salvar</button>
    </div>`);
  $('#btnSalvarEditUser').onclick = async () => {
    try {
      const body = { nome: $('#eUNome').value, role: $('#eURole').value, ativo: $('#eUAtivo').value==='1' };
      const pw = $('#eUPass').value;
      if (pw) body.password = pw;
      await api('/api/users/'+id, {method:'PUT', body});
      closeModal(); viewUsuarios($('#content'));
    } catch(e){ alert(e.message); }
  };
};
