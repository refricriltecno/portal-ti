import React, { useState, useEffect } from 'react';
import { 
  Menu, X, LayoutDashboard, FileText, Building2, Upload, TrendingUp, Clock, 
  CheckCircle, AlertCircle, Plus, Eye, Edit, Search, CheckSquare, Trash2, Download, 
  AlertTriangle, ChevronDown, DollarSign, Calendar, Calculator, User, Lock, History, Shield, LogOut, Receipt, Phone, PieChart, Copy
} from 'lucide-react';

const API_URL = "http://127.0.0.1:8001";

const LISTA_FILIAIS = ["00 - Administrativo", "01 - Matriz", "08 - Porto Alegre", "09 - Floripa", "06 - Blumenau", "12 - Itajaí", "03 - Joinville", "05 - Londrina", "17 - CD São Paulo", "22 - São Paulo (Itaim)", "21 - São Paulo (Osasco)", "20 - São Paulo (Guarulhos)", "10 - São Paulo", "02 - CD Vila Velha", "24 - CD Goiânia", "15 - Teresina", "18 - Belo Horizonte", "11 - Vila Velha", "07 - CD Içara", "13 - CD Paraíba", "27 - Brasília", "14 - Goiania"];
const LISTA_CENTROS_CUSTO = ["TI - Infraestrutura", "TI - Sistemas", "TI - Geral", "Administrativo", "Comercial", "Financeiro", "RH", "Logística"];
const LISTA_EMPRESAS_RATEIO = LISTA_FILIAIS;
const LISTA_STATUS = ["Pendente", "Enviado Quarti", "Enviado Refricril", "Pago"];

// Componente para seleção de mês com dropdown customizado
const MesSelector = ({ value, onChange, label = "Mês Referência" }) => {
  const [open, setOpen] = React.useState(false);
  const meses = [
    { valor: '01', nome: 'Janeiro' }, { valor: '02', nome: 'Fevereiro' }, { valor: '03', nome: 'Março' },
    { valor: '04', nome: 'Abril' }, { valor: '05', nome: 'Maio' }, { valor: '06', nome: 'Junho' },
    { valor: '07', nome: 'Julho' }, { valor: '08', nome: 'Agosto' }, { valor: '09', nome: 'Setembro' },
    { valor: '10', nome: 'Outubro' }, { valor: '11', nome: 'Novembro' }, { valor: '12', nome: 'Dezembro' }
  ];
  
  const [ano, setAno] = React.useState(new Date().getFullYear());
  const mesAtual = value ? value.split('-')[1] : '';
  
  const mesNome = meses.find(m => m.valor === mesAtual)?.nome || 'Selecione';
  
  return (
    <div className="relative w-full">
      <label className="text-xs font-bold text-slate-300 block mb-2">{label}</label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-cyan-500/50 rounded-lg p-3 text-white text-left flex items-center justify-between transition-all hover:shadow-lg hover:shadow-cyan-500/10"
      >
        <span className="flex items-center gap-2">
          <Calendar size={16} className="text-cyan-400" />
          <span>{mesNome} / {ano}</span>
        </span>
        <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute z-50 top-full mt-2 w-full bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-3 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-3 pb-3 border-b border-slate-700">
            <button type="button" onClick={() => setAno(ano - 1)} className="p-1 hover:bg-slate-800 rounded text-cyan-400">◀</button>
            <span className="font-bold text-white">{ano}</span>
            <button type="button" onClick={() => setAno(ano + 1)} className="p-1 hover:bg-slate-800 rounded text-cyan-400">▶</button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {meses.map(m => (
              <button
                key={m.valor}
                type="button"
                onClick={() => {
                  onChange(`${ano}-${m.valor}`);
                  setOpen(false);
                }}
                className={`p-2 rounded-lg text-sm font-bold transition-all ${
                  mesAtual === m.valor
                    ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/30'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {m.nome.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState({ username: '', role: '' });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePage, setActivePage] = useState('dashboard');
  
  const [contratos, setContratos] = useState([]);
  const [faturas, setFaturas] = useState([]);
  const [numerosTelefonia, setNumerosTelefonia] = useState([]);
  const [logs, setLogs] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [credenciais, setCredenciais] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ tipo: '', texto: '' });
  
  const [modalContrato, setModalContrato] = useState(false);
  const [modalFatura, setModalFatura] = useState(false);
  const [modalStatus, setModalStatus] = useState(false);
  const [modalTelefonia, setModalTelefonia] = useState(false);
  const [modalCsvTim, setModalCsvTim] = useState(false);
  const [modalCsvInventario, setModalCsvInventario] = useState(false); // Novo
  const [modalCredenciais, setModalCredenciais] = useState(false);
  const [modalProfile, setModalProfile] = useState(false);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [editandoContrato, setEditandoContrato] = useState(null);
  const [editandoFatura, setEditandoFatura] = useState(null);
  const [editandoTelefonia, setEditandoTelefonia] = useState(null);
  const [rateioAtivo, setRateioAtivo] = useState(false);
  const [empresasSelecionadas, setEmpresasSelecionadas] = useState([]);
  const [statusTemp, setStatusTemp] = useState(null);
  const [abaTelefonia, setAbaTelefonia] = useState('Todos'); // Mudado para ver tudo junto se quiser
  const [editandoCredencial, setEditandoCredencial] = useState(null);

  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [newUserForm, setNewUserForm] = useState({ username: '', password: '', role: 'user' });
  const [passwordForm, setPasswordForm] = useState({ senhaAtual: '', senhaNova: '', senhaConfirm: '' });
  const [authMode, setAuthMode] = useState('login'); // 'login' ou 'register'
  const [formContrato, setFormContrato] = useState({});
  const [formFatura, setFormFatura] = useState({});
  const [formStatus, setFormStatus] = useState({ data_pagamento: '', observacoes: '' });
  const [formTelefonia, setFormTelefonia] = useState({ numero: '', valor: '', descricao: '', mes_referencia: '', setor: '', filial: '' });
  const [fileCsv, setFileCsv] = useState(null);
  const [formCredencial, setFormCredencial] = useState({});

  const authHeader = { 'Authorization': `Bearer ${token}` };

  const handleLogin = async (e) => {
    e.preventDefault(); setLoading(true);
    const fd = new FormData(); fd.append('username', loginForm.username); fd.append('password', loginForm.password);
    try {
      const res = await fetch(`${API_URL}/token`, { method: 'POST', body: fd });
      if(!res.ok) throw new Error();
      const data = await res.json();
      localStorage.setItem('token', data.access_token); setToken(data.access_token); setUser({ username: data.username, role: data.role });
      setMsg({tipo: 'success', texto: 'Bem-vindo!'});
    } catch { setMsg({tipo: 'error', texto: 'Usuário ou senha incorretos.'}); }
    setLoading(false);
  };

  const logout = () => { localStorage.removeItem('token'); setToken(null); setUser({ username: '', role: '' }); };

  const handleChangePassword = async (e) => {
    e.preventDefault(); setLoading(true);
    if (passwordForm.senhaNova.length < 6) { setMsg({tipo: 'error', texto: 'Senha deve ter no mínimo 6 caracteres'}); setLoading(false); return; }
    if (passwordForm.senhaNova !== passwordForm.senhaConfirm) { setMsg({tipo: 'error', texto: 'Senhas não conferem'}); setLoading(false); return; }
    
    const fd = new FormData(); 
    fd.append('current_password', passwordForm.senhaAtual); 
    fd.append('new_password', passwordForm.senhaNova);
    try {
      const res = await fetch(`${API_URL}/me/password`, { method: 'PUT', headers: authHeader, body: fd });
      if(!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao alterar senha');
      }
      setMsg({tipo: 'success', texto: 'Senha alterada com sucesso!'});
      setPasswordForm({ senhaAtual: '', senhaNova: '', senhaConfirm: '' });
      setModalProfile(false);
    } catch (err) { setMsg({tipo: 'error', texto: err.message || 'Erro ao alterar senha'}); }
    setLoading(false);
  };

  useEffect(() => { 
    if(token) {
      try { 
        const payload = JSON.parse(atob(token.split('.')[1])); 
        setUser({ username: payload.sub, role: payload.role }); 
        carregarDados(); 
        
        // Auto-refresh a cada 30 segundos para atualizações em tempo real
        const interval = setInterval(() => {
          carregarDados();
          if(activePage === 'telefonia') carregarTelefonia();
          if(activePage === 'historico') carregarLogs();
          if(activePage === 'admin') carregarUsuarios();
          if(activePage === 'credenciais') carregarCredenciais();
        }, 30000);
        
        return () => clearInterval(interval);
      } catch { logout(); }
    }
  }, [token, activePage]);

  const carregarDados = async () => {
    try {
      const [resC, resF, resS] = await Promise.all([
        fetch(`${API_URL}/contratos/`, {headers: authHeader}), 
        fetch(`${API_URL}/faturas/`, {headers: authHeader}), 
        fetch(`${API_URL}/dashboard/stats`, {headers: authHeader})
      ]);
      if(resC.status === 401) { logout(); return; }
      const dContratos = await resC.json();
      setContratos(dContratos);
      setFaturas(await resF.json());
      const dStats = await resS.json();
      const custoMensalReal = dContratos.reduce((acc, c) => acc + (parseFloat(c.valor_total) / (parseInt(c.tempo_contrato_meses)||1)), 0);
      setStats({...dStats, valor_contratos_mensal: custoMensalReal});
    } catch (err) { console.error(err); }
  };

  const carregarTelefonia = async () => {
      const url = abaTelefonia === 'Todos' ? `${API_URL}/telefonia/` : `${API_URL}/telefonia/?operadora=${abaTelefonia}`;
      const res = await fetch(url, {headers: authHeader});
      setNumerosTelefonia(await res.json());
  };

  useEffect(() => { if(activePage === 'telefonia') carregarTelefonia(); }, [activePage, abaTelefonia]);

  const carregarLogs = async () => { const res = await fetch(`${API_URL}/logs/`, {headers: authHeader}); setLogs(await res.json()); };
  const carregarUsuarios = async () => { const res = await fetch(`${API_URL}/users/`, {headers: authHeader}); setUsersList(await res.json()); };
  
  const criarNovoUsuario = async (e) => {
    e.preventDefault(); setLoading(true);
    if (newUserForm.username.length < 3) { setMsg({tipo: 'error', texto: 'Usuário deve ter no mínimo 3 caracteres'}); setLoading(false); return; }
    if (newUserForm.password.length < 6) { setMsg({tipo: 'error', texto: 'Senha deve ter no mínimo 6 caracteres'}); setLoading(false); return; }
    
    const fd = new FormData(); fd.append('username', newUserForm.username); fd.append('password', newUserForm.password);
    try {
      const res = await fetch(`${API_URL}/register`, { method: 'POST', body: fd, headers: authHeader });
      if(!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Erro ao criar usuário'); }
      setMsg({tipo: 'success', texto: 'Usuário criado com sucesso!'});
      setNewUserForm({ username: '', password: '', role: 'user' });
      carregarUsuarios();
    } catch (err) { setMsg({tipo: 'error', texto: err.message || 'Erro ao criar usuário'}); }
    setLoading(false);
  };
  
  const deletarUsuario = async (id) => {
    if (!confirm('Tem certeza que deseja deletar este usuário?')) return;
    try {
      const res = await fetch(`${API_URL}/users/${id}`, { method: 'DELETE', headers: authHeader });
      if(!res.ok) throw new Error('Erro ao deletar');
      setMsg({tipo: 'success', texto: 'Usuário deletado!'});
      carregarUsuarios();
    } catch (err) { setMsg({tipo: 'error', texto: err.message}); }
  };
  const carregarCredenciais = async () => { const res = await fetch(`${API_URL}/credenciais/`, {headers: authHeader}); setCredenciais(await res.json()); };

  // --- ACTIONS ---
  const handleSubmitContrato = async (e) => {
    e.preventDefault(); setLoading(true);
    const fd = new FormData();
    Object.keys(formContrato).forEach(k => { if(formContrato[k]!==null && formContrato[k]!==undefined) fd.append(k, formContrato[k]); });
    fd.append('tem_rateio', rateioAtivo); fd.append('empresas_rateio', empresasSelecionadas.join(", "));
    const url = editandoContrato ? `${API_URL}/contratos/${editandoContrato}` : `${API_URL}/contratos/`;
    const method = editandoContrato ? 'PUT' : 'POST';
    try { await fetch(url, { method: method, headers: authHeader, body: fd }); setModalContrato(false); carregarDados(); } catch (error) { alert("Erro ao salvar contrato"); }
    setLoading(false);
  };

  const handleSubmitFatura = async (e) => {
    e.preventDefault(); 
    if (!formFatura.contrato_id) { alert("Selecione um contrato!"); return; }
    if (!formFatura.valor) { alert("Digite o valor original!"); return; }
    if (!editandoFatura && !formFatura.arquivo) { alert("Anexe o Boleto!"); return; }
    setLoading(true);
    const fd = new FormData();
    Object.keys(formFatura).forEach(k => { if(formFatura[k]!==null) fd.append(k, formFatura[k]); });
    const url = editandoFatura ? `${API_URL}/faturas/${editandoFatura}` : `${API_URL}/faturas/`;
    const method = editandoFatura ? 'PUT' : 'POST';
    try { const res = await fetch(url, { method: method, headers: authHeader, body: fd }); if(!res.ok) throw new Error(); setModalFatura(false); carregarDados(); } catch (err) { alert("Erro ao salvar fatura."); }
    setLoading(false);
  };

  const handleUploadTim = async (e) => {
      e.preventDefault();
      if(!fileCsv) return;
      setLoading(true);
      const fd = new FormData();
      fd.append('mes_referencia', formTelefonia.mes_referencia);
      fd.append('arquivo', fileCsv);
      try {
          await fetch(`${API_URL}/telefonia/upload/tim`, { method: 'POST', headers: authHeader, body: fd });
          setModalCsvTim(false); carregarTelefonia();
      } catch { alert("Erro no upload"); }
      setLoading(false);
  };

  const handleUploadInventario = async (e) => {
      e.preventDefault();
      if(!fileCsv) return;
      setLoading(true);
      const fd = new FormData();
      fd.append('mes_referencia', formTelefonia.mes_referencia);
      fd.append('arquivo', fileCsv);
      try {
          await fetch(`${API_URL}/telefonia/upload/inventario`, { method: 'POST', headers: authHeader, body: fd });
          setModalCsvInventario(false); carregarTelefonia();
      } catch { alert("Erro no upload inventário"); }
      setLoading(false);
  };

  const handleTelefoniaForm = async (e) => {
      e.preventDefault();
      setLoading(true);
      const fd = new FormData();
      fd.append('numero', formTelefonia.numero);
      fd.append('valor', formTelefonia.valor);
      fd.append('descricao', formTelefonia.descricao);
      fd.append('mes_referencia', formTelefonia.mes_referencia);
      fd.append('setor', formTelefonia.setor || '');
      fd.append('filial', formTelefonia.filial || '');
      fd.append('operadora', abaTelefonia === 'Todos' ? 'Manual' : abaTelefonia);
      
      const url = editandoTelefonia ? `${API_URL}/telefonia/${editandoTelefonia}` : `${API_URL}/telefonia/`;
      const method = editandoTelefonia ? 'PUT' : 'POST';
      
      await fetch(url, { method: method, headers: authHeader, body: fd });
      setLoading(false); setModalTelefonia(false); carregarTelefonia();
  };

  const confirmarMudancaStatus = async () => {
    const fd = new FormData();
    fd.append('status', statusTemp.novoStatus);
    if(formStatus.data_pagamento) fd.append('data_pagamento', formStatus.data_pagamento);
    if(formStatus.observacoes) fd.append('observacoes', formStatus.observacoes);
    await fetch(`${API_URL}/faturas/${statusTemp.id}/status`, { method: 'PUT', headers: authHeader, body: fd });
    setModalStatus(false); carregarDados();
  };

  const criarUsuario = async (e) => {
    e.preventDefault();
    const fd = new FormData(); fd.append('username', newUserForm.username); fd.append('password', newUserForm.password); fd.append('role', newUserForm.role);
    const res = await fetch(`${API_URL}/users/`, { method: 'POST', headers: authHeader, body: fd });
    if(res.ok) { setMsg({tipo:'success', texto:'Criado!'}); carregarUsuarios(); }
  };

  const formatarMes = (mesIso) => { if(!mesIso) return '-'; const [ano, mes] = mesIso.split('-'); return `${mes}/${ano}`; }

  const abrirModalNovoContrato = () => {
    setEditandoContrato(null);
    setFormContrato({ 
      nome_amigavel: '', filial: '', fornecedor_razao: '', cnpj_fornecedor: '', 
      fornecedor2_razao: null, cnpj_fornecedor2: '', centro_custo: '', tipo: 'Serviço', 
      valor_total: '', tempo_contrato_meses: '', identificadores: '', info_adicional: '', 
      dia_vencimento: '', data_inicio_cobranca: '', arquivo: null, numero_circuito: '' 
    });
    setRateioAtivo(false); setEmpresasSelecionadas([]); setModalContrato(true);
  };

  const abrirModalEditarContrato = (c) => {
    setEditandoContrato(c.id);
    setFormContrato({ ...c, arquivo: null });
    setRateioAtivo(c.tem_rateio);
    setEmpresasSelecionadas(c.empresas_rateio ? c.empresas_rateio.split(', ') : []);
    setModalContrato(true);
  };

  const abrirModalNovaFatura = () => {
    setEditandoFatura(null);
    const hoje = new Date();
    const mesAtual = `${hoje.getFullYear()}-${String(hoje.getMonth()+1).padStart(2, '0')}`;
    setFormFatura({ contrato_id: '', mes_referencia: mesAtual, valor: '', data_vencimento: '', numero_circuito: '', desconto: 0, acrescimo: 0, status: 'Pendente', observacoes: '', arquivo: null, arquivo_nf: null });
    setModalFatura(true);
  };

  const abrirModalEditarFatura = (f) => {
    setEditandoFatura(f.id);
    setFormFatura({ ...f, contrato_id: f.contrato_id, valor: f.valor, arquivo: null, arquivo_nf: null });
    setModalFatura(true);
  };
  
  const abrirModalEditarTelefonia = (n) => {
      setEditandoTelefonia(n.id);
      setFormTelefonia({ 
          numero: n.numero, valor: n.valor, descricao: n.descricao, 
          mes_referencia: n.mes_referencia, setor: n.setor || '', filial: n.filial || '' 
      });
      setModalTelefonia(true);
  };

  const excluirContrato = async (id) => { if(confirm("Confirmar exclusão?")) { await fetch(`${API_URL}/contratos/${id}`, {method:'DELETE', headers: authHeader}); carregarDados(); }};
  const excluirNumero = async (id) => { if(confirm("Excluir número?")) { await fetch(`${API_URL}/telefonia/${id}`, {method:'DELETE', headers: authHeader}); carregarTelefonia(); }};

  const handleSubmitCredencial = async (e) => {
    e.preventDefault(); setLoading(true);
    const fd = new FormData();
    Object.keys(formCredencial).forEach(k => { if(formCredencial[k]!==null && formCredencial[k]!==undefined) fd.append(k, formCredencial[k]); });
    const url = editandoCredencial ? `${API_URL}/credenciais/${editandoCredencial}` : `${API_URL}/credenciais/`;
    const method = editandoCredencial ? 'PUT' : 'POST';
    try { 
      await fetch(url, { method: method, headers: authHeader, body: fd }); 
      setModalCredenciais(false); 
      carregarCredenciais(); 
      setMsg({tipo: 'success', texto: 'Credencial salva com sucesso!'});
    } catch (error) { 
      setMsg({tipo: 'error', texto: 'Erro ao salvar credencial'});
    }
    setLoading(false);
  };

  const excluirCredencial = async (id) => { 
    if(confirm("Confirmar exclusão?")) { 
      await fetch(`${API_URL}/credenciais/${id}`, {method:'DELETE', headers: authHeader}); 
      carregarCredenciais(); 
    }
  };

  const abrirModalNovaCredencial = () => {
    setEditandoCredencial(null);
    setFormCredencial({ nome_servico: '', url_acesso: '', usuario: '', senha: '', descricao: '', email: '', telefone: '', responsavel: '' });
    setModalCredenciais(true);
  };

  const abrirModalEditarCredencial = (c) => {
    setEditandoCredencial(c.id);
    setFormCredencial({ ...c });
    setModalCredenciais(true);
  };

  // --- CALCULO RATEIO TELEFONIA ---
  const rateioTelefonia = numerosTelefonia.reduce((acc, curr) => {
      const filial = curr.filial || "Indefinido";
      acc[filial] = (acc[filial] || 0) + curr.valor;
      return acc;
  }, {});

  if (!token) return (
    <div className="flex h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-gradient-to-br from-slate-900 to-slate-950 p-8 rounded-2xl border border-slate-800/50 shadow-2xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-cyan-500/50">
              <Building2 className="text-white" size={32}/>
            </div>
            <h1 className="text-3xl font-black bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">Portal TI</h1>
            <p className="text-sm text-slate-500 mt-2">Gestão de Contratos e Telefonia</p>
          </div>

          {msg.texto && <div className={`mb-4 p-3 rounded-lg text-sm font-semibold ${msg.tipo === 'success' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>{msg.texto}</div>}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 mb-2 block">Usuário</label>
              <input 
                required
                placeholder="Digite seu usuário" 
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white placeholder-slate-500 transition-all focus:outline-none focus:border-slate-600"
                value={loginForm.username} 
                onChange={e=>setLoginForm({...loginForm, username:e.target.value})} 
              />
            </div>
            
            <div>
              <label className="text-xs font-bold text-slate-300 mb-2 block">Senha</label>
              <input 
                required
                type="password" 
                placeholder="Digite sua senha" 
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white placeholder-slate-500 transition-all focus:outline-none focus:border-slate-600"
                value={loginForm.password} 
                onChange={e=>setLoginForm({...loginForm, password:e.target.value})} 
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">© 2026 Portal TI - Sistema de Gestão</p>
      </div>
    </div>
  );

  const FaturaRow = ({ f }) => {
    const contrato = contratos.find(item => item.id === f.contrato_id);
    const valTotalContrato = parseFloat(contrato?.valor_total) || 0;
    const mesesContrato = parseInt(contrato?.tempo_contrato_meses) || 1;
    const valMensalEsperado = valTotalContrato / mesesContrato;
    const valOriginalFatura = parseFloat(f.valor) || 0;
    const valAcrescimo = parseFloat(f.acrescimo) || 0;
    const valDesconto = parseFloat(f.desconto) || 0;
    const valFinal = valOriginalFatura + valAcrescimo - valDesconto;
    const temDivergencia = Math.abs(valFinal - valMensalEsperado) > 1.00;

    return (
      <tr className="hover:bg-slate-700/30 border-b border-slate-700/50">
        <td className="p-4"><div className="text-white font-medium">{contrato?.nome_amigavel}</div><div className="text-[10px] text-slate-500">Base Esperada: R$ {valMensalEsperado.toLocaleString(undefined, {minimumFractionDigits:2})}</div></td>
        <td className="p-4 text-slate-300 text-sm"><div>{formatarMes(f.mes_referencia)}</div><div className="text-xs text-slate-500 font-mono">{f.data_vencimento ? f.data_vencimento.split('-').reverse().join('/') : '-'}</div></td>
        <td className="p-4"><div className="flex flex-col"><div className="flex items-center gap-2"><span className={`font-bold ${temDivergencia ? 'text-rose-400' : 'text-emerald-400'}`}>R$ {valFinal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>{temDivergencia && <div className="group relative"><AlertCircle size={16} className="text-rose-500 animate-pulse cursor-help" /><div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 bg-rose-900/95 text-white text-xs p-3 rounded-lg shadow-xl border border-rose-500 hidden group-hover:block z-50"><strong>Divergência!</strong><div className="mt-1 grid grid-cols-2 gap-1 text-[10px] opacity-90"><span>Contrato:</span> <span className="text-right">R$ {valMensalEsperado.toFixed(2)}</span><span>Pago:</span> <span className="text-right">R$ {valFinal.toFixed(2)}</span></div></div></div>}</div>{(valAcrescimo > 0 || valDesconto > 0) && <div className="text-[10px] text-slate-500 mt-0.5">Orig: {valOriginalFatura.toFixed(0)} {valAcrescimo > 0 ? `+ ${valAcrescimo}` : ''} {valDesconto > 0 ? `- ${valDesconto}` : ''}</div>}</div></td>
        <td className="p-4"><select value={f.status} onChange={(e)=>{setStatusTemp({id:f.id, novoStatus:e.target.value}); setFormStatus({data_pagamento:'', observacoes:f.observacoes||''}); setModalStatus(true);}} className="bg-slate-900 border border-slate-700 rounded text-xs p-1 text-slate-300 outline-none hover:border-slate-500 transition-colors">{LISTA_STATUS.map(s=><option key={s} value={s}>{s}</option>)}</select></td>
        <td className="p-4 text-xs text-slate-400 max-w-[120px] truncate" title={f.observacoes}>{f.observacoes || '-'}</td>
        <td className="p-4 text-right flex justify-end gap-3"><div className="flex gap-2"><a href={`${API_URL}/${f.caminho_arquivo}`} target="_blank" className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1" title="Boleto"><FileText size={16}/></a>{f.caminho_nf && <a href={`${API_URL}/${f.caminho_nf}`} target="_blank" className="text-purple-400 hover:text-purple-300 flex items-center gap-1" title="Nota Fiscal"><Receipt size={16}/></a>}</div><button onClick={()=>abrirModalEditarFatura(f)} className="text-blue-400 hover:text-blue-300"><Edit size={16}/></button></td>
      </tr>
    );
  };

  return (
    <div className="flex h-screen bg-slate-950 text-white font-sans selection:bg-cyan-500/30">
      <div className={`${sidebarOpen ? 'w-72' : 'w-20'} bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-r border-slate-800/50 transition-all duration-300 flex flex-col z-20 shadow-2xl`}>
        <div className="p-6 flex items-center gap-4 border-b border-slate-800/50"><div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/50"><Building2 className="text-white" size={24}/></div>{sidebarOpen && <div><h1 className="font-black text-lg bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">Portal TI</h1><p className="text-xs text-slate-400">v2.5 Pro</p></div>}</div>
        <nav className="flex-1 px-4 space-y-2 mt-6">
          <button onClick={()=>setActivePage('dashboard')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='dashboard'?'bg-gradient-to-r from-cyan-600/20 to-blue-600/20 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-500/10':'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}><LayoutDashboard size={20}/> {sidebarOpen && <span className="font-semibold">Dashboard</span>}</button>
          <button onClick={()=>setActivePage('contratos')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='contratos'?'bg-gradient-to-r from-purple-600/20 to-pink-600/20 text-purple-400 border border-purple-500/30 shadow-lg shadow-purple-500/10':'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}><FileText size={20}/> {sidebarOpen && <span className="font-semibold">Contratos</span>}</button>
          <button onClick={()=>setActivePage('faturas')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='faturas'?'bg-gradient-to-r from-pink-600/20 to-rose-600/20 text-pink-400 border border-pink-500/30 shadow-lg shadow-pink-500/10':'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}><Upload size={20}/> {sidebarOpen && <span className="font-semibold">Faturas</span>}</button>
          <button onClick={()=>setActivePage('telefonia')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='telefonia'?'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 text-blue-400 border border-blue-500/30 shadow-lg shadow-blue-500/10':'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}`}><Phone size={20}/> {sidebarOpen && <span className="font-semibold">Telefonia</span>}</button>
          {user.role === 'admin' && <><div className="my-4 border-t border-slate-800/50"></div><button onClick={()=>{setActivePage('historico'); carregarLogs();}} className={`w-full flex gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='historico'?'bg-amber-500/10 text-amber-400 border border-amber-500/30':'text-slate-400 hover:bg-slate-800/50'}`}><History size={20}/> {sidebarOpen && <span className="font-semibold">Histórico</span>}</button><button onClick={()=>{setActivePage('credenciais'); carregarCredenciais();}} className={`w-full flex gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='credenciais'?'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30':'text-slate-400 hover:bg-slate-800/50'}`}><Lock size={20}/> {sidebarOpen && <span className="font-semibold">Credenciais</span>}</button><button onClick={()=>{setActivePage('admin'); carregarUsuarios();}} className={`w-full flex gap-3 px-4 py-3 rounded-lg transition-all ${activePage==='admin'?'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30':'text-slate-400 hover:bg-slate-800/50'}`}><Shield size={20}/> {sidebarOpen && <span className="font-semibold">Admin</span>}</button></>}
        </nav>
        <div className="p-4 border-t border-slate-800"><button onClick={logout} className="w-full py-3 rounded-xl text-slate-400 hover:bg-slate-800 flex justify-center gap-2"><LogOut size={18}/> {sidebarOpen && "Sair"}</button></div>
      </div>

      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <header className="h-20 border-b border-slate-800/30 flex items-center px-8 justify-between backdrop-blur-md bg-gradient-to-r from-slate-950/80 via-slate-950/80 to-slate-900/80 z-10 shadow-xl">
          <button onClick={()=>setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-slate-800/50 rounded-lg transition-all"><Menu className="text-slate-300"/></button>
          <div className="flex items-center gap-4">
            {msg.texto && <div className={`px-4 py-2 rounded-lg text-sm font-semibold ${msg.tipo === 'success' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>{msg.texto}</div>}
            <div className="flex items-center gap-3 pl-4 border-l border-slate-800 cursor-pointer hover:opacity-80 transition-all" onClick={()=>setModalProfile(true)}>
              <div className="text-right"><p className="text-sm font-bold text-white">{user.username}</p><p className="text-xs text-slate-400 capitalize">{user.role}</p></div>
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30"><User size={18} className="text-white"/></div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-8 scrollbar-thin scrollbar-thumb-slate-800">
          
          {activePage === 'dashboard' && <div className="space-y-8 animate-in fade-in"><div className="flex items-center justify-between mb-8"><h1 className="text-4xl font-black bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">Dashboard</h1><div className="text-sm text-slate-400">{new Date().toLocaleDateString('pt-BR', {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'})}</div></div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-cyan-500/10 via-blue-500/5 to-slate-900/10 p-8 rounded-2xl border border-cyan-500/20 hover:border-cyan-500/40 shadow-xl hover:shadow-2xl hover:shadow-cyan-500/20 transition-all group">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider">Previsto</h3>
                <DollarSign size={24} className="text-cyan-400 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-4xl font-black text-cyan-400">R$ {stats.valor_contratos_mensal?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
              <p className="text-xs text-slate-500 mt-2">Custo mensal total em contratos</p>
            </div>
            
            <div className="bg-gradient-to-br from-emerald-500/10 via-green-500/5 to-slate-900/10 p-8 rounded-2xl border border-emerald-500/20 hover:border-emerald-500/40 shadow-xl hover:shadow-2xl hover:shadow-emerald-500/20 transition-all group">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider">Realizado</h3>
                <CheckCircle size={24} className="text-emerald-400 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-4xl font-black text-emerald-400">R$ {stats.valor_pago?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
              <p className="text-xs text-slate-500 mt-2">Total já pago</p>
            </div>
            
            <div className="bg-gradient-to-br from-rose-500/10 via-red-500/5 to-slate-900/10 p-8 rounded-2xl border border-rose-500/20 hover:border-rose-500/40 shadow-xl hover:shadow-2xl hover:shadow-rose-500/20 transition-all group">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider">Pendente</h3>
                <AlertCircle size={24} className="text-rose-400 group-hover:scale-110 transition-transform" />
              </div>
              <p className="text-4xl font-black text-rose-400">R$ {stats.valor_pendente?.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
              <p className="text-xs text-slate-500 mt-2">À receber</p>
            </div>
          </div></div>}

          {/* TELEFONIA */}
          {activePage === 'telefonia' && (
              <div className="space-y-8 animate-in fade-in">
                  <div className="flex justify-between items-center mb-8"><h1 className="text-4xl font-black bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Telefonia</h1><div className="flex bg-slate-800/50 p-1 rounded-lg border border-slate-700">
                    <button onClick={()=>setAbaTelefonia('Todos')} className={`px-4 py-2 rounded-md font-bold transition-all ${abaTelefonia==='Todos'?'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/30':'text-slate-400 hover:text-white'}`}>Tudo</button>
                    <button onClick={()=>setAbaTelefonia('Tim')} className={`px-4 py-2 rounded-md font-bold transition-all ${abaTelefonia==='Tim'?'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-500/30':'text-slate-400 hover:text-white'}`}>Tim</button>
                    <button onClick={()=>setAbaTelefonia('Vivo')} className={`px-4 py-2 rounded-md font-bold transition-all ${abaTelefonia==='Vivo'?'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30':'text-slate-400 hover:text-white'}`}>Vivo</button>
                  </div></div>
                  
                  {/* DASHBOARD RATEIO POR FILIAL (NOVO) */}
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-4">
                      {Object.entries(rateioTelefonia).map(([fil, val]) => (
                          <div key={fil} className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                              <div className="text-[10px] text-slate-400 uppercase font-bold truncate">{fil}</div>
                              <div className="text-lg font-bold text-emerald-400">R$ {val.toFixed(2)}</div>
                          </div>
                      ))}
                  </div>

                  <div className="flex justify-end gap-3">
                      <button onClick={()=>setModalCsvInventario(true)} className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg font-bold flex gap-2 shadow-lg"><FileText size={18}/> Importar Inventário (CSV)</button>
                      {abaTelefonia === 'Tim' && <button onClick={()=>setModalCsvTim(true)} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-bold flex gap-2 shadow-lg"><Upload size={18}/> CSV Tim</button>}
                      <button onClick={()=>{setEditandoTelefonia(null); setFormTelefonia({numero:'', valor:'', descricao:'', mes_referencia:'', setor:'', filial:''}); setModalTelefonia(true);}} className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg font-bold flex gap-2"><Plus size={18}/> Manual</button>
                  </div>
                  <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-900/50 text-slate-400 text-xs uppercase"><tr><th className="p-4">Número</th><th className="p-4">Descrição</th><th className="p-4">Setor</th><th className="p-4">Filial</th><th className="p-4">Valor</th><th className="p-4 text-right">Ações</th></tr></thead><tbody>{numerosTelefonia.map(n=><tr key={n.id} className="hover:bg-slate-700/30 border-b border-slate-700/50"><td className="p-4 font-mono text-white">{n.numero}</td><td className="p-4 text-slate-400 text-sm max-w-[200px] truncate">{n.descricao}</td><td className="p-4 text-slate-400 text-sm">{n.setor}</td><td className="p-4 text-slate-400 text-sm">{n.filial}</td><td className="p-4 font-bold text-emerald-400">R$ {n.valor.toFixed(2)}</td><td className="p-4 text-right flex justify-end gap-2"><button onClick={()=>abrirModalEditarTelefonia(n)} className="text-slate-400 hover:text-white"><Edit size={16}/></button><button onClick={()=>excluirNumero(n.id)} className="text-slate-500 hover:text-rose-500"><Trash2 size={16}/></button></td></tr>)}</tbody></table></div>
              </div>
          )}

          {activePage === 'contratos' && <div className="space-y-6 animate-in fade-in"><div className="flex justify-between items-center"><h1 className="text-3xl font-bold">Contratos</h1><button onClick={abrirModalNovoContrato} className="bg-cyan-600 px-6 py-2 rounded-xl font-bold flex gap-2"><Plus/> Novo</button></div><div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-900/50 text-slate-400 text-xs uppercase"><tr><th className="p-4">Nome</th><th className="p-4">Fornecedor</th><th className="p-4">Valor Total</th><th className="p-4">Mensal (Calc)</th><th className="p-4 text-right">Ações</th></tr></thead><tbody>{contratos.map(c=>{ const valTotal = parseFloat(c.valor_total) || 0; const meses = parseInt(c.tempo_contrato_meses) || 1; const mensal = valTotal / meses; return (<tr key={c.id} className="hover:bg-slate-700/30"><td className="p-4">{c.nome_amigavel}</td><td className="p-4 text-slate-300">{c.fornecedor_razao}</td><td className="p-4 text-slate-400">R$ {valTotal.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td><td className="p-4"><div className="font-bold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded w-fit border border-emerald-500/20">R$ {mensal.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div></td><td className="p-4 text-right flex justify-end gap-2"><button onClick={()=>abrirModalEditarContrato(c)}><Edit size={16} className="text-slate-400 hover:text-white"/></button><button onClick={()=>excluirContrato(c.id)}><Trash2 size={16} className="text-slate-400 hover:text-rose-500"/></button></td></tr>)})}</tbody></table></div></div>}
          {activePage === 'faturas' && <div className="space-y-6 animate-in fade-in"><div className="flex justify-between items-center"><h1 className="text-3xl font-bold">Lançamentos</h1><button onClick={abrirModalNovaFatura} className="bg-pink-600 px-6 py-2 rounded-xl font-bold flex gap-2"><Upload/> Lançar</button></div><div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-900/50 text-slate-400 text-xs uppercase"><tr><th className="p-4">Contrato</th><th className="p-4">Ref/Venc</th><th className="p-4">Valor</th><th className="p-4">Status</th><th className="p-4">Obs</th><th className="p-4 text-right">Ações</th></tr></thead><tbody>{faturas.map(f=><FaturaRow key={f.id} f={f}/>)}</tbody></table></div></div>}
          {activePage === 'historico' && user.role === 'admin' && <div className="space-y-6"><h1 className="text-3xl font-bold">Histórico</h1><div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden"><table className="w-full text-left text-sm text-slate-300"><thead className="bg-slate-900/50 text-slate-400"><tr><th className="p-4">Data</th><th className="p-4">Usuário</th><th className="p-4">Detalhes</th></tr></thead><tbody>{logs.map(l=><tr key={l.id} className="hover:bg-slate-700/30"><td className="p-4">{new Date(l.data_hora).toLocaleString()}</td><td className="p-4 font-bold text-white">{l.usuario}</td><td className="p-4">{l.acao} - {l.detalhes}</td></tr>)}</tbody></table></div></div>}
          {activePage === 'credenciais' && user.role === 'admin' && <div className="space-y-6 animate-in fade-in"><div className="flex justify-between items-center"><h1 className="text-3xl font-bold">Credenciais da Terceirizada</h1><button onClick={abrirModalNovaCredencial} className="bg-emerald-600 px-6 py-2 rounded-xl font-bold flex gap-2"><Plus/> Nova</button></div><div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{credenciais.map(c=><div key={c.id} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 hover:border-slate-600 transition-all group"><div className="flex justify-between items-start mb-3"><div className="flex-1"><h3 className="font-bold text-cyan-400 text-lg">{c.nome_servico}</h3><p className="text-xs text-slate-400 mt-1">{c.descricao}</p></div><div className="flex gap-2"><button onClick={()=>abrirModalEditarCredencial(c)} className="text-slate-500 hover:text-blue-400 transition-colors"><Edit size={16}/></button><button onClick={()=>excluirCredencial(c.id)} className="text-slate-500 hover:text-rose-500 transition-colors"><Trash2 size={16}/></button></div></div><div className="space-y-2 text-sm"><div className="flex items-center gap-2"><span className="text-slate-500 w-16">URL:</span><a href={c.url_acesso} target="_blank" rel="noopener" className="text-cyan-400 hover:underline truncate">{c.url_acesso}</a></div><div className="flex items-center gap-2"><span className="text-slate-500 w-16">User:</span><span className="text-slate-300 font-mono">{c.usuario}</span><button className="text-slate-500 hover:text-slate-300" onClick={()=>navigator.clipboard.writeText(c.usuario)}><Copy size={14}/></button></div><div className="flex items-center gap-2"><span className="text-slate-500 w-16">Pass:</span><span className="text-slate-400 select-none">{'•'.repeat(8)}</span><button className="text-slate-500 hover:text-slate-300" onClick={()=>navigator.clipboard.writeText(c.senha)} title="Copiar senha"><Copy size={14}/></button></div>{c.email && <div className="flex items-center gap-2"><span className="text-slate-500 w-16">Email:</span><span className="text-slate-300">{c.email}</span></div>}{c.telefone && <div className="flex items-center gap-2"><span className="text-slate-500 w-16">Tel:</span><span className="text-slate-300">{c.telefone}</span></div>}{c.responsavel && <div className="flex items-center gap-2"><span className="text-slate-500 w-16">Resp:</span><span className="text-slate-300">{c.responsavel}</span></div>}</div><div className="mt-3 pt-3 border-t border-slate-700/50"><span className="text-[10px] text-slate-500">Atualizado: {new Date(c.data_atualizacao).toLocaleDateString('pt-BR')}</span></div></div>)}</div></div>}
          {activePage === 'admin' && user.role === 'admin' && <div className="space-y-6 animate-in fade-in"><h1 className="text-3xl font-bold">Gestão de Usuários</h1><div className="grid grid-cols-1 lg:grid-cols-3 gap-6"><div className="bg-gradient-to-br from-slate-800 to-slate-900 p-6 rounded-2xl border border-emerald-500/30"><h3 className="font-bold text-emerald-400 mb-4 flex items-center gap-2"><Plus size={18}/> Novo Usuário</h3><form onSubmit={criarNovoUsuario} className="space-y-4"><div><label className="text-xs font-bold text-slate-300 mb-1 block">Usuário</label><input required placeholder="Digite o usuário" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white" value={newUserForm.username} onChange={e=>setNewUserForm({...newUserForm, username:e.target.value})}/></div><div><label className="text-xs font-bold text-slate-300 mb-1 block">Senha</label><input required type="password" placeholder="Mínimo 6 caracteres" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white" value={newUserForm.password} onChange={e=>setNewUserForm({...newUserForm, password:e.target.value})}/></div><button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-500 py-2 rounded-lg font-bold text-white transition-all disabled:opacity-50">{loading ? 'Criando...' : 'Criar Usuário'}</button></form></div><div className="lg:col-span-2 bg-slate-800/50 p-6 rounded-2xl border border-slate-700/50"><h3 className="font-bold text-cyan-400 mb-4 flex items-center gap-2"><User size={18}/> Usuários Ativos</h3><div className="space-y-2 max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">{usersList.length === 0 ? <p className="text-slate-500 text-center py-4">Nenhum usuário cadastrado</p> : usersList.map(u=><div key={u.id} className="flex justify-between items-center bg-slate-900/50 p-3 rounded-lg border border-slate-700 hover:border-slate-600 transition-all"><div className="flex-1"><p className="font-mono text-white">{u.username}</p><p className="text-xs text-slate-500">{u.is_active ? '✓ Ativo' : '✗ Inativo'}</p></div><div className="flex items-center gap-3"><span className={`text-xs px-2 py-1 rounded ${u.role === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>{u.role === 'admin' ? '⚙️ Admin' : '👤 Usuário'}</span><button onClick={()=>deletarUsuario(u.id)} className="text-slate-500 hover:text-rose-500 transition-colors p-1"><Trash2 size={16}/></button></div></div>)}</div></div></div></div>}
        </main>
      </div>

      {modalStatus && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"><div className="bg-slate-900 p-6 rounded-xl w-96 border border-slate-700"><h3 className="text-xl font-bold mb-4">Status: {statusTemp?.novoStatus}</h3>{statusTemp?.novoStatus==='Pago'&&<input type="date" className="w-full bg-slate-800 p-2 mb-4 rounded text-white" onChange={e=>setFormStatus({...formStatus, data_pagamento:e.target.value})}/>}<textarea className="w-full bg-slate-800 p-2 mb-4 rounded text-white" placeholder="Obs..." value={formStatus.observacoes} onChange={e=>setFormStatus({...formStatus, observacoes:e.target.value})}></textarea><div className="flex gap-2"><button onClick={()=>setModalStatus(false)} className="flex-1 bg-slate-700 py-2 rounded">Cancelar</button><button onClick={confirmarMudancaStatus} className="flex-1 bg-emerald-600 py-2 rounded">Salvar</button></div></div></div>}

      {/* MODAL CSV TIM */}
      {/* MODAL CSV TIM */}
      {modalCsvTim && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-2xl w-full max-w-md border border-blue-500/20 p-7 shadow-2xl"><div className="flex items-center gap-3 mb-6"><div className="p-2 bg-blue-500/20 rounded-lg"><Upload size={20} className="text-blue-400" /></div><h2 className="text-xl font-bold text-white">Importar CSV Tim</h2></div><form onSubmit={handleUploadTim} className="space-y-5"><MesSelector value={formTelefonia.mes_referencia} onChange={e=>setFormTelefonia({...formTelefonia, mes_referencia:e})} /><div className="border-2 border-dashed border-blue-500/30 hover:border-blue-500/60 rounded-xl p-8 text-center cursor-pointer relative transition-all bg-blue-500/5 group"><input type="file" required accept=".csv" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e=>setFileCsv(e.target.files[0])}/><Upload size={32} className="mx-auto text-blue-400/50 group-hover:text-blue-400 mb-2 transition-colors" /><p className="text-sm font-semibold text-slate-300">{fileCsv ? <span className="text-blue-400">{fileCsv.name}</span> : "Clique ou arraste para selecionar"}</p><p className="text-xs text-slate-500 mt-1">Arquivo CSV (.csv)</p></div><div className="flex justify-end gap-3 pt-2"><button type="button" onClick={()=>setModalCsvTim(false)} className="px-4 py-2 text-slate-400 hover:bg-slate-800 rounded-lg transition-all">Cancelar</button><button type="submit" disabled={loading} className="bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-2 rounded-lg font-bold text-white hover:shadow-lg hover:shadow-blue-500/30 transition-all">{loading?'Importando...':'Importar'}</button></div></form></div></div>}

      {/* MODAL CSV INVENTÁRIO */}
      {modalCsvInventario && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-2xl w-full max-w-md border border-purple-500/20 p-7 shadow-2xl"><div className="flex items-center gap-3 mb-6"><div className="p-2 bg-purple-500/20 rounded-lg"><Upload size={20} className="text-purple-400" /></div><h2 className="text-xl font-bold text-white">Importar Inventário</h2></div><form onSubmit={handleUploadInventario} className="space-y-5"><MesSelector value={formTelefonia.mes_referencia} onChange={e=>setFormTelefonia({...formTelefonia, mes_referencia:e})} /><div className="border-2 border-dashed border-purple-500/30 hover:border-purple-500/60 rounded-xl p-8 text-center cursor-pointer relative transition-all bg-purple-500/5 group"><input type="file" required accept=".csv" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e=>setFileCsv(e.target.files[0])}/><Upload size={32} className="mx-auto text-purple-400/50 group-hover:text-purple-400 mb-2 transition-colors" /><p className="text-sm font-semibold text-slate-300">{fileCsv ? <span className="text-purple-400">{fileCsv.name}</span> : "numeros.csv"}</p><p className="text-xs text-slate-500 mt-1">Arquivo CSV com números de telefones</p></div><div className="flex justify-end gap-3 pt-2"><button type="button" onClick={()=>setModalCsvInventario(false)} className="px-4 py-2 text-slate-400 hover:bg-slate-800 rounded-lg transition-all">Cancelar</button><button type="submit" disabled={loading} className="bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-2 rounded-lg font-bold text-white hover:shadow-lg hover:shadow-purple-500/30 transition-all">{loading?'Importando...':'Importar'}</button></div></form></div></div>}

      {/* MODAL TELEFONIA MANUAL / EDITAR */}
      {modalTelefonia && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-2xl w-full max-w-lg border border-slate-700/50 p-7 shadow-2xl"><h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2"><Phone size={20} className="text-emerald-400" />{editandoTelefonia ? 'Editar Número' : `Novo Lançamento`}</h2><form onSubmit={handleTelefoniaForm} className="space-y-5"><div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-bold text-slate-300 mb-2 block">Número</label><input required className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-emerald-500/50 rounded-lg p-3 text-white font-mono transition-all" placeholder="(11) 99999-9999" value={formTelefonia.numero} onChange={e=>setFormTelefonia({...formTelefonia, numero:e.target.value})}/></div><div><label className="text-xs font-bold text-slate-300 mb-2 block">Descrição</label><input className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-emerald-500/50 rounded-lg p-3 text-white transition-all" placeholder="Ex: João Silva" value={formTelefonia.descricao} onChange={e=>setFormTelefonia({...formTelefonia, descricao:e.target.value})}/></div></div>
      <div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-bold text-slate-300 mb-2 block">Filial</label><select className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-emerald-500/50 rounded-lg p-3 text-white transition-all" value={formTelefonia.filial} onChange={e=>setFormTelefonia({...formTelefonia, filial:e.target.value})}><option value="">Selecione...</option>{LISTA_FILIAIS.map(f=><option key={f} value={f}>{f}</option>)}</select></div><div><label className="text-xs font-bold text-slate-300 mb-2 block">Centro de Custo</label><select className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-emerald-500/50 rounded-lg p-3 text-white transition-all" value={formTelefonia.setor} onChange={e=>setFormTelefonia({...formTelefonia, setor:e.target.value})}><option value="">Selecione...</option>{LISTA_CENTROS_CUSTO.map(c=><option key={c} value={c}>{c}</option>)}</select></div></div>
      <div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-bold text-slate-300 mb-2 block">Valor (R$)</label><input required type="number" step="0.01" className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-emerald-500/50 rounded-lg p-3 text-white font-mono transition-all" placeholder="0,00" value={formTelefonia.valor} onChange={e=>setFormTelefonia({...formTelefonia, valor:e.target.value})}/></div><div><MesSelector value={formTelefonia.mes_referencia} onChange={e=>setFormTelefonia({...formTelefonia, mes_referencia:e})} /></div></div><div className="flex justify-end gap-3 pt-4 border-t border-slate-700"><button type="button" onClick={()=>setModalTelefonia(false)} className="px-4 py-2 text-slate-400 hover:bg-slate-800 rounded-lg transition-all">Cancelar</button><button type="submit" className="bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-2 rounded-lg font-bold text-white hover:shadow-lg hover:shadow-emerald-500/30 transition-all">Salvar</button></div></form></div></div>}

      {/* MODAL CONTRATO COMPLETO */}
      {modalContrato && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-slate-900 rounded-2xl w-full max-w-5xl border border-slate-700 shadow-2xl flex flex-col max-h-[90vh]"><div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between"><div><h2 className="text-2xl font-bold text-white">{editandoContrato ? 'Editar' : 'Novo'} Contrato</h2></div><button onClick={()=>setModalContrato(false)}><X className="text-slate-500"/></button></div><form onSubmit={handleSubmitContrato} className="p-8 overflow-y-auto space-y-6 scrollbar-thin scrollbar-thumb-slate-700">
      
      <div className="grid grid-cols-2 gap-6"><div><label className="block text-xs font-bold text-slate-300 mb-2">Nome Amigável *</label><input required className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white" value={formContrato.nome_amigavel} onChange={e=>setFormContrato({...formContrato, nome_amigavel:e.target.value})} /></div><div><label className="block text-xs font-bold text-slate-300 mb-2">Filial *</label><select required className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white" value={formContrato.filial} onChange={e=>setFormContrato({...formContrato, filial:e.target.value})}><option value="">Selecione...</option>{LISTA_FILIAIS.map(f=><option key={f} value={f}>{f}</option>)}</select></div></div>

      <div className="bg-slate-800/30 p-4 rounded-xl border border-slate-700/30"><h3 className="text-sm font-bold text-cyan-400 uppercase mb-4">Dados do Contrato</h3>
      <div className="grid grid-cols-2 gap-4"><div><label className="text-xs text-slate-400">Tipo *</label><select required className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white" value={formContrato.tipo} onChange={e=>setFormContrato({...formContrato, tipo:e.target.value})}><option value="">Selecione...</option><option value="Serviço">Serviço</option><option value="Produto">Produto</option><option value="Misto">Misto</option></select></div><div><label className="text-xs text-slate-400">Centro de Custo *</label><select required className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white" value={formContrato.centro_custo} onChange={e=>setFormContrato({...formContrato, centro_custo:e.target.value})}><option value="">Selecione...</option>{LISTA_CENTROS_CUSTO.map(c=><option key={c} value={c}>{c}</option>)}</select></div></div>
      <div className="grid grid-cols-3 gap-4"><div><label className="text-xs text-slate-400">Valor Total (R$) *</label><input required type="number" step="0.01" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formContrato.valor_total} onChange={e=>setFormContrato({...formContrato, valor_total:e.target.value})}/></div><div><label className="text-xs text-slate-400">Duração (Meses) *</label><input required type="number" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formContrato.tempo_contrato_meses} onChange={e=>setFormContrato({...formContrato, tempo_contrato_meses:e.target.value})}/></div><div><label className="text-xs text-slate-400">Valor Mensal (Calc.)</label><input disabled type="text" className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg p-2.5 text-emerald-400 font-bold" value={`R$ ${(parseFloat(formContrato.valor_total || 0) / parseInt(formContrato.tempo_contrato_meses || 1)).toLocaleString('pt-BR', {minimumFractionDigits: 2})}`}/></div></div>
      <div className="grid grid-cols-2 gap-4"><div><label className="text-xs text-slate-400">Data Início Cobrança</label><input type="date" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white" value={formContrato.data_inicio_cobranca} onChange={e=>setFormContrato({...formContrato, data_inicio_cobranca:e.target.value})}/></div><div><label className="text-xs text-slate-400">Dia Vencimento</label><input type="number" min="1" max="31" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white" value={formContrato.dia_vencimento} onChange={e=>setFormContrato({...formContrato, dia_vencimento:e.target.value})}/></div></div></div>

      <div className="bg-slate-800/30 p-4 rounded-xl border border-slate-700/30"><h3 className="text-sm font-bold text-purple-400 uppercase mb-4">Fornecedores</h3>
      <div className="space-y-3"><div className="grid grid-cols-3 gap-3"><div><label className="text-xs text-slate-400">Fornecedor 1 - Razão Social *</label><input required className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white text-sm" value={formContrato.fornecedor_razao} onChange={e=>setFormContrato({...formContrato, fornecedor_razao:e.target.value})}/></div><div><label className="text-xs text-slate-400">CNPJ 1 *</label><input required className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formContrato.cnpj_fornecedor} onChange={e=>setFormContrato({...formContrato, cnpj_fornecedor:e.target.value})}/></div><div><label className="text-xs text-slate-400">Circ. Fornecedor 1</label><input className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formContrato.numero_circuito || ''} onChange={e=>setFormContrato({...formContrato, numero_circuito:e.target.value})}/></div></div>
      <div className="border-t border-slate-700/50 pt-3"><div><label className="text-xs text-slate-400"><input type="checkbox" checked={!!formContrato.fornecedor2_razao} onChange={e=>setFormContrato({...formContrato, fornecedor2_razao: e.target.checked ? '' : null})} /> Tem fornecedor 2?</label></div>{formContrato.fornecedor2_razao !== null && <div className="grid grid-cols-2 gap-3 mt-3"><div><label className="text-xs text-slate-400">Fornecedor 2 - Razão Social</label><input className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white text-sm" value={formContrato.fornecedor2_razao || ''} onChange={e=>setFormContrato({...formContrato, fornecedor2_razao:e.target.value})}/></div><div><label className="text-xs text-slate-400">CNPJ 2</label><input className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formContrato.cnpj_fornecedor2 || ''} onChange={e=>setFormContrato({...formContrato, cnpj_fornecedor2:e.target.value})}/></div></div>}</div></div></div>

      <div className="bg-slate-800/30 p-4 rounded-xl border border-slate-700/30"><h3 className="text-sm font-bold text-blue-400 uppercase mb-4">Observações e Rateio</h3>
      <div className="space-y-3"><div><label className="text-xs text-slate-400">Identificadores (Tags/Ref)</label><input className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white text-sm" value={formContrato.identificadores || ''} onChange={e=>setFormContrato({...formContrato, identificadores:e.target.value})}/></div>
      <div><label className="text-xs text-slate-400">Informações Adicionais</label><textarea className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white text-sm h-16" value={formContrato.info_adicional || ''} onChange={e=>setFormContrato({...formContrato, info_adicional:e.target.value})}></textarea></div>
      <div><label className="text-xs text-slate-400"><input type="checkbox" checked={rateioAtivo} onChange={e=>setRateioAtivo(e.target.checked)} /> Este contrato é rateado entre filiais?</label>{rateioAtivo && <div className="mt-3 bg-slate-900 p-3 rounded-lg border border-slate-700"><label className="text-xs text-slate-400 block mb-2">Selecione as filiais:</label><div className="grid grid-cols-2 gap-2">{LISTA_EMPRESAS_RATEIO.map(emp=><label key={emp} className="text-xs text-slate-300"><input type="checkbox" checked={empresasSelecionadas.includes(emp)} onChange={e=>e.target.checked ? setEmpresasSelecionadas([...empresasSelecionadas, emp]) : setEmpresasSelecionadas(empresasSelecionadas.filter(x=>x!==emp))} /> {emp}</label>)}</div></div>}</div></div></div>

      <div className="flex justify-end gap-3 pt-4 border-t border-slate-700"><button type="button" onClick={()=>setModalContrato(false)} className="px-6 py-2 text-slate-400 hover:bg-slate-800 rounded-lg">Cancelar</button><button type="submit" className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg shadow-lg transition-all">{loading ? 'Salvando...' : 'Salvar Contrato'}</button></div>
      </form></div></div>}
      
      {modalFatura && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-slate-900 rounded-2xl w-full max-w-4xl border border-slate-700 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden"><div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center"><div><h2 className="text-2xl font-bold text-white">{editandoFatura ? 'Editar' : 'Lançar'} Fatura</h2></div><button onClick={()=>setModalFatura(false)}><X className="text-slate-500 hover:text-white"/></button></div><form onSubmit={handleSubmitFatura} className="p-8 overflow-y-auto flex-1 grid grid-cols-1 md:grid-cols-2 gap-8 scrollbar-thin scrollbar-thumb-slate-700"> {/* Conteúdo do form fatura mantido */} <div className="space-y-6"><div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50"><h3 className="text-sm font-bold text-cyan-500 uppercase mb-4 flex items-center gap-2"><FileText size={16}/> Geral</h3><div className="space-y-4"><div><label className="block text-xs text-slate-400 mb-1">Contrato</label><select required className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white outline-none" value={formFatura.contrato_id} onChange={e=>setFormFatura({...formFatura, contrato_id:e.target.value})}><option value="">Selecione...</option>{contratos.map(c=><option key={c.id} value={c.id}>{c.nome_amigavel} - {c.fornecedor_razao}</option>)}</select></div><div className="grid grid-cols-2 gap-4"><div><MesSelector value={formFatura.mes_referencia} onChange={e=>setFormFatura({...formFatura, mes_referencia:e})} /></div><div><label className="block text-xs font-bold text-slate-300 mb-2">Vencimento</label><input required type="date" className="w-full bg-gradient-to-r from-slate-800 to-slate-850 border border-slate-700 hover:border-cyan-500/50 rounded-lg p-3 text-white transition-all hover:shadow-lg hover:shadow-cyan-500/10" value={formFatura.data_vencimento} onChange={e=>setFormFatura({...formFatura, data_vencimento:e.target.value})}/></div></div><div><label className="block text-xs text-slate-400 mb-1">Circuito</label><input placeholder="Ex: 123456" className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white" value={formFatura.numero_circuito} onChange={e=>setFormFatura({...formFatura, numero_circuito:e.target.value})}/></div></div></div><div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50"><h3 className="text-sm font-bold text-slate-400 uppercase mb-4 flex items-center gap-2"><Upload size={16}/> Arquivos</h3><div className="space-y-4"><div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/50 rounded-xl p-4 text-center cursor-pointer relative transition-colors"><input type="file" accept=".pdf" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e=>setFormFatura({...formFatura, arquivo:e.target.files[0]})}/><p className="text-xs text-slate-300">{formFatura.arquivo ? <span className="text-cyan-400">{formFatura.arquivo.name}</span> : "Boleto Bancário (PDF)"}</p></div><div className="border-2 border-dashed border-slate-700 hover:border-purple-500/50 rounded-xl p-4 text-center cursor-pointer relative transition-colors"><input type="file" accept=".pdf" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e=>setFormFatura({...formFatura, arquivo_nf:e.target.files[0]})}/><p className="text-xs text-slate-300">{formFatura.arquivo_nf ? <span className="text-purple-400">{formFatura.arquivo_nf.name}</span> : "Nota Fiscal (Opcional)"}</p></div></div></div></div><div className="bg-slate-800/30 p-6 rounded-xl border border-slate-700/30 flex flex-col"><h3 className="text-sm font-bold text-emerald-500 uppercase mb-6 flex items-center gap-2"><Calculator size={16}/> Valores</h3><div className="space-y-6 flex-1"><div><label className="block text-xs font-bold text-slate-300 mb-1">Valor Original (Boleto)</label><input required type="number" step="0.01" className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-4 pr-4 py-3 text-white font-mono text-lg" value={formFatura.valor} onChange={e=>setFormFatura({...formFatura, valor:e.target.value})}/></div><div className="grid grid-cols-2 gap-4"><div><label className="block text-xs text-rose-400 mb-1">Descontos (-)</label><input type="number" step="0.01" className="w-full bg-slate-900 border border-rose-900/30 rounded-lg p-2 text-rose-400" value={formFatura.desconto} onChange={e=>setFormFatura({...formFatura, desconto:e.target.value})}/></div><div><label className="block text-xs text-blue-400 mb-1">Acréscimos (+)</label><input type="number" step="0.01" className="w-full bg-slate-900 border border-blue-900/30 rounded-lg p-2 text-blue-400" value={formFatura.acrescimo} onChange={e=>setFormFatura({...formFatura, acrescimo:e.target.value})}/></div></div><div className="bg-slate-900 p-4 rounded-xl border border-slate-800 mt-4"><p className="text-xs text-slate-500 mb-1">Total a Pagar</p><p className="text-3xl font-bold text-emerald-400">R$ {((parseFloat(formFatura.valor||0) + parseFloat(formFatura.acrescimo||0)) - parseFloat(formFatura.desconto||0)).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p></div><div><label className="block text-xs text-slate-400 mb-1">Observações</label><textarea className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white text-sm" rows="3" value={formFatura.observacoes} onChange={e=>setFormFatura({...formFatura, observacoes:e.target.value})}></textarea></div></div><div className="pt-6 mt-6 border-t border-slate-700/50 flex gap-3"><button type="button" onClick={()=>setModalFatura(false)} className="flex-1 py-3 rounded-xl text-slate-400 hover:bg-slate-800 font-medium">Cancelar</button><button type="submit" disabled={loading} className="flex-1 py-3 rounded-xl bg-pink-600 hover:bg-pink-500 text-white font-bold shadow-lg">{loading?'...': editandoFatura ? 'Salvar' : 'Lançar'}</button></div></div></form></div></div>}

      {/* MODAL CREDENCIAIS */}
      {modalCredenciais && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-slate-900 rounded-2xl w-full max-w-2xl border border-slate-700 shadow-2xl"><div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between"><h2 className="text-2xl font-bold text-white">{editandoCredencial ? 'Editar' : 'Nova'} Credencial</h2><button onClick={()=>setModalCredenciais(false)}><X className="text-slate-500"/></button></div><form onSubmit={handleSubmitCredencial} className="p-6 space-y-4 overflow-y-auto max-h-[80vh] scrollbar-thin scrollbar-thumb-slate-700"><div className="grid grid-cols-2 gap-4"><div><label className="text-xs text-slate-400">Nome do Serviço *</label><input required className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.nome_servico} onChange={e=>setFormCredencial({...formCredencial, nome_servico:e.target.value})}/></div><div><label className="text-xs text-slate-400">URL de Acesso *</label><input required type="url" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.url_acesso} onChange={e=>setFormCredencial({...formCredencial, url_acesso:e.target.value})}/></div></div><div><label className="text-xs text-slate-400">Descrição</label><input className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.descricao} onChange={e=>setFormCredencial({...formCredencial, descricao:e.target.value})}/></div><div className="grid grid-cols-2 gap-4"><div><label className="text-xs text-slate-400">Usuário *</label><input required className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formCredencial.usuario} onChange={e=>setFormCredencial({...formCredencial, usuario:e.target.value})}/></div><div><label className="text-xs text-slate-400">Senha *</label><input required type="password" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white font-mono" value={formCredencial.senha} onChange={e=>setFormCredencial({...formCredencial, senha:e.target.value})}/></div></div><div className="grid grid-cols-2 gap-4"><div><label className="text-xs text-slate-400">Email</label><input type="email" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.email} onChange={e=>setFormCredencial({...formCredencial, email:e.target.value})}/></div><div><label className="text-xs text-slate-400">Telefone</label><input className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.telefone} onChange={e=>setFormCredencial({...formCredencial, telefone:e.target.value})}/></div></div><div><label className="text-xs text-slate-400">Responsável</label><input className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white" value={formCredencial.responsavel} onChange={e=>setFormCredencial({...formCredencial, responsavel:e.target.value})}/></div><div className="flex justify-end gap-2 pt-4"><button type="button" onClick={()=>setModalCredenciais(false)} className="px-4 py-2 text-slate-400">Cancelar</button><button type="submit" className="bg-emerald-600 px-6 py-2 rounded-lg font-bold text-white">{loading ? 'Salvando...' : 'Salvar'}</button></div></form></div></div>}

      {/* MODAL PERFIL */}
      {modalProfile && <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-slate-900 rounded-2xl w-full max-w-md border border-slate-700 shadow-2xl"><div className="p-6 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center"><h2 className="text-2xl font-bold text-white flex items-center gap-2"><User size={24} className="text-cyan-400"/> Meu Perfil</h2><button onClick={()=>setModalProfile(false)}><X className="text-slate-500 hover:text-white"/></button></div><form onSubmit={handleChangePassword} className="p-6 space-y-6"><div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50"><p className="text-xs text-slate-400 mb-1">Usuário</p><p className="text-lg font-bold text-cyan-400">{user.username}</p><p className="text-xs text-slate-500 mt-2 capitalize">Role: {user.role}</p></div><div className="space-y-4"><div><label className="text-xs font-bold text-slate-300 mb-2 block">Senha Atual</label><input required type="password" placeholder="Digite sua senha atual" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white placeholder-slate-500 transition-all focus:outline-none focus:border-slate-600" value={passwordForm.senhaAtual} onChange={e=>setPasswordForm({...passwordForm, senhaAtual:e.target.value})}/></div><div><label className="text-xs font-bold text-slate-300 mb-2 block">Nova Senha</label><input required type="password" placeholder="Mínimo 6 caracteres" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white placeholder-slate-500 transition-all focus:outline-none focus:border-slate-600" value={passwordForm.senhaNova} onChange={e=>setPasswordForm({...passwordForm, senhaNova:e.target.value})}/></div><div><label className="text-xs font-bold text-slate-300 mb-2 block">Confirmar Nova Senha</label><input required type="password" placeholder="Repita a nova senha" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white placeholder-slate-500 transition-all focus:outline-none focus:border-slate-600" value={passwordForm.senhaConfirm} onChange={e=>setPasswordForm({...passwordForm, senhaConfirm:e.target.value})}/></div></div><div className="flex gap-3 pt-4 border-t border-slate-700"><button type="button" onClick={()=>setModalProfile(false)} className="flex-1 px-4 py-2 text-slate-400 hover:bg-slate-800 rounded-lg transition-all">Cancelar</button><button type="submit" disabled={loading} className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-2 rounded-lg transition-all disabled:opacity-50">{loading ? 'Alterando...' : 'Alterar Senha'}</button></div></form></div></div>}
    </div>
  );
}

export default App;