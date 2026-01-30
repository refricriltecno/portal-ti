# Sistema de Perfis e Permissões - Portal TI

## 📋 Visão Geral
Sistema de gestão de usuários com 3 perfis distintos, cada um com suas permissões específicas.

---

## 👥 Perfis Disponíveis

### 1️⃣ **ADMIN (Administrador TI)**
**Descrição:** Acesso total ao sistema com permissões para gerenciar todos os recursos.

**Permissões:**
- ✅ Dashboard - Visualizar estatísticas gerais
- ✅ Contratos - Visualizar, criar, editar e deletar contratos
- ✅ Faturas - Visualizar, criar, editar e deletar faturas
- ✅ Telefonia - Visualizar, criar, editar e deletar números telefônicos
- ✅ Histórico - Visualizar logs detalhados do sistema
- ✅ Credenciais - Visualizar, criar, editar e deletar credenciais
- ✅ Gestão de Usuários - Criar, visualizar e deletar usuários

**Rota de Login:** `/token`
**Identificador:** `role = "admin"`

---

### 2️⃣ **NORMAL (Usuário Padrão)**
**Descrição:** Acesso aos recursos principais do sistema para consulta e gerenciamento básico.

**Permissões:**
- ✅ Dashboard - Visualizar estatísticas gerais
- ✅ Contratos - Visualizar e criar contratos (editar/deletar apenas seus próprios)
- ✅ Faturas - Visualizar e criar faturas
- ✅ Telefonia - Visualizar números telefônicos
- ✅ Histórico - Visualizar histórico geral

**Restrições:**
- ❌ Credenciais - Sem acesso
- ❌ Gestão de Usuários - Sem acesso
- ❌ Logs administrativos - Sem acesso

**Rota de Login:** `/token`
**Identificador:** `role = "normal"`

---

### 3️⃣ **TERCERIZADO (Prestador de Serviço)**
**Descrição:** Acesso a recursos principais e credenciais para operacionalizar serviços terceirizados.

**Permissões:**
- ✅ Dashboard - Visualizar estatísticas gerais
- ✅ Contratos - Visualizar contratos relacionados
- ✅ Faturas - Visualizar faturas
- ✅ Telefonia - Visualizar números telefônicos
- ✅ Histórico - Visualizar histórico
- ✅ **Credenciais - VISUALIZAR APENAS** (não pode criar/editar/deletar)

**Restrições:**
- ❌ Gestão de Usuários - Sem acesso
- ❌ Logs administrativos - Sem acesso

**Rota de Login:** `/token`
**Identificador:** `role = "tercerizado"`

---

## 🔐 Rotas de API por Perfil

| Rota | Admin | Normal | Tercerizado | Método |
|------|-------|--------|-------------|--------|
| `/token` | ✅ | ✅ | ✅ | POST |
| `/me` | ✅ | ✅ | ✅ | GET |
| `/dashboard/` | ✅ | ✅ | ✅ | GET |
| `/contratos/` | ✅ | ✅ | ✅ | GET |
| `/contratos/` | ✅ | ✅ | ❌ | POST |
| `/contratos/{id}` | ✅ | ✅* | ❌ | PUT |
| `/contratos/{id}` | ✅ | ❌ | ❌ | DELETE |
| `/faturas/` | ✅ | ✅ | ✅ | GET |
| `/faturas/` | ✅ | ✅ | ❌ | POST |
| `/faturas/{id}` | ✅ | ✅* | ❌ | PUT |
| `/faturas/{id}` | ✅ | ❌ | ❌ | DELETE |
| `/telefonia/` | ✅ | ✅ | ✅ | GET |
| `/telefonia/` | ✅ | ✅ | ❌ | POST |
| `/telefonia/{id}` | ✅ | ✅* | ❌ | PUT |
| `/telefonia/{id}` | ✅ | ❌ | ❌ | DELETE |
| `/credenciais/` | ✅ | ❌ | ✅** | GET |
| `/credenciais/` | ✅ | ❌ | ❌ | POST |
| `/credenciais/{id}` | ✅ | ❌ | ❌ | PUT |
| `/credenciais/{id}` | ✅ | ❌ | ❌ | DELETE |
| `/historico/` | ✅ | ✅ | ✅ | GET |
| `/logs/` | ✅ | ❌ | ❌ | GET |
| `/users/` | ✅ | ❌ | ❌ | GET |
| `/users/` | ✅ | ❌ | ❌ | POST |
| `/users/{id}` | ✅ | ❌ | ❌ | DELETE |

**Legenda:**
- ✅ = Permissão total
- ❌ = Sem permissão
- ✅* = Apenas seus próprios registros
- ✅** = Apenas visualização (sem editar/deletar)

---

## 🎨 Interface Frontend

### Sidebar - Opções Visíveis por Perfil

**Admin:**
- Dashboard
- Contratos
- Faturas
- Telefonia
- Histórico
- Credenciais
- Admin (Gestão de Usuários)

**Normal:**
- Dashboard
- Contratos
- Faturas
- Telefonia
- Histórico
- *(Sem Credenciais)*
- *(Sem Admin)*

**Tercerizado:**
- Dashboard
- Contratos
- Faturas
- Telefonia
- Histórico
- Credenciais (visualização)
- *(Sem Admin)*

---

## 🔧 Implementação Técnica

### Backend (FastAPI)

**Funções de Verificação:**

```python
def verificar_permissao(usuario: User, rotas_permitidas: list):
    """Verifica se o usuário tem permissão para acessar a rota"""
    if usuario.role not in rotas_permitidas:
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar este recurso")

def check_admin(usuario: User):
    """Verifica se o usuário é admin"""
    if usuario.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso apenas para administradores")

def check_can_view_credentials(usuario: User):
    """Verifica se o usuário pode visualizar credenciais"""
    if usuario.role not in ["admin", "tercerizado"]:
        raise HTTPException(status_code=403, detail="Acesso apenas para administradores ou terceirizados")
```

**Mapeamento de Permissões:**

```python
PERMISSOES = {
    "dashboard": ["admin", "normal", "tercerizado"],
    "faturas": ["admin", "normal", "tercerizado"],
    "contratos": ["admin", "normal", "tercerizado"],
    "telefonia": ["admin", "normal", "tercerizado"],
    "historico": ["admin", "normal", "tercerizado"],
    "credenciais": ["admin", "tercerizado"],
    "usuarios": ["admin"],
    "logs": ["admin"],
}
```

### Frontend (React)

**Renderização Condicional:**

```jsx
// Histórico - Disponível para todos
<button onClick={()=>{setActivePage('historico'); carregarLogs();}} 
  className={...}>
  <History size={20}/> {sidebarOpen && <span>Histórico</span>}
</button>

// Credenciais - Admin e Tercerizado
{(user.role === 'admin' || user.role === 'tercerizado') && 
  <button onClick={()=>{setActivePage('credenciais'); carregarCredenciais();}} 
    className={...}>
    <Lock size={20}/> {sidebarOpen && <span>Credenciais</span>}
  </button>
}

// Admin - Apenas Admin
{user.role === 'admin' && 
  <button onClick={()=>{setActivePage('admin'); carregarUsuarios();}} 
    className={...}>
    <Shield size={20}/> {sidebarOpen && <span>Admin</span>}
  </button>
}
```

---

## 📝 Como Criar Usuários

### Via Admin Panel

1. Faça login com uma conta **Admin**
2. Acesse **Admin** na sidebar
3. Preencha:
   - **Usuário:** Nome do novo usuário
   - **Senha:** Mínimo 6 caracteres
   - **Perfil:** Selecione entre Admin, Normal ou Tercerizado
4. Clique em **Criar Usuário**

### Roles Disponíveis

- `admin` - Administrador TI
- `normal` - Usuário Padrão
- `tercerizado` - Prestador de Serviço

---

## 🔄 Fluxo de Autenticação

1. **Login** → `/token` (POST) → Retorna JWT Token
2. **Token Armazenado** → localStorage como `token`
3. **Requisições Subsequentes** → Header: `Authorization: Bearer {token}`
4. **Verificação** → Middleware compara `user.role` com `PERMISSOES`
5. **Resposta** → 200 OK (autorizado) ou 403 Forbidden (sem permissão)

---

## 📊 Diagrama de Acesso

```
┌─────────────────────────────────────────────────────────────┐
│                   SISTEMA DE GESTÃO TI                      │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              ┌─────▼──┐ ┌────▼──┐ ┌───▼─────┐
              │ ADMIN  │ │NORMAL │ │TERCEIRO │
              └────┬───┘ └───┬───┘ └──┬──────┘
                   │         │        │
        ┌──────────┴────────┬┴───────┬┴───────┐
        │                   │        │        │
    ┌───▼────┐  ┌──────┐ ┌─▼────┐ ┌┴────┐ ┌─┴────┐
    │Dashboard│  │Contratos│Faturas│Telefonia│Credenciais│
    └────────┘  └────┬────┘ │      │       └──┬────┘
                 └────┴──────┴──────┴──────────┘
                      (Acesso Variável)
        
    Admin:       Acesso Total a Tudo
    Normal:      Dashboard, Contratos, Faturas, Telefonia, Histórico
    Tercerizado: Dashboard, Contratos, Faturas, Telefonia, Histórico, Credenciais(View Only)
```

---

## ⚠️ Notas Importantes

1. **Primeira Conta:** O primeiro usuário criado deve ser **admin**
2. **Token JWT:** Válido até o logout
3. **Senha:** Mínimo 6 caracteres (armazenada com bcrypt)
4. **Foto de Perfil:** Cada usuário pode fazer upload de sua própria foto
5. **Histórico:** Registra todas as ações do usuário (auditoria)
6. **Credenciais:** Apenas admin pode gerenciar; tercerizado pode visualizar

---

## 🚀 Testes Recomendados

1. **Teste com Admin:**
   - Crie um novo usuário com perfil "tercerizado"
   - Crie uma credencial
   - Verifique acesso a todas as abas

2. **Teste com Normal:**
   - Faça login
   - Verifique que Credenciais não aparece na sidebar
   - Tente acessar `/credenciais/` diretamente (deve retornar 403)

3. **Teste com Tercerizado:**
   - Faça login
   - Verifique que Credenciais aparece
   - Visualize credenciais
   - Tente editar/deletar (deve retornar 403)

---

**Versão:** 2.5 Pro
**Última Atualização:** 28 de Janeiro de 2026
**Status:** ✅ Funcional
