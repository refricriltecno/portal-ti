# 🎯 GUIA RÁPIDO - Sistema de Perfis e Permissões

## ⚡ Resumo Executivo

O sistema foi atualizado com um robusto sistema de controle de acesso baseado em 3 perfis:

- **Admin (TI)** - Acesso total
- **Normal** - Acesso a ferramentas principais  
- **Tercerizado** - Acesso a ferramentas + credenciais (visualização)

---

## 🔧 Como Usar

### 1. Criar um Novo Usuário Tercerizado

1. Faça login como **Admin**
2. Clique em **Admin** na sidebar
3. Preencha os dados:
   - Usuário: `tercerizado_1`
   - Senha: `senha123`
   - Role: selecione **"user"** (será ajustado manualmente)

> **Nota:** Atualmente o formulário frontend não permite selecionar "tercerizado". Será necessário atualizar o select ou fazer via SQL:
```sql
UPDATE users SET role = 'tercerizado' WHERE username = 'tercerizado_1';
```

### 2. Usuário Tercerizado Faz Login

```
Username: tercerizado_1
Password: senha123
```

### 3. O Que Ele Pode Ver

Na sidebar:
- ✅ Dashboard
- ✅ Contratos
- ✅ Faturas
- ✅ Telefonia
- ✅ Histórico
- ✅ **Credenciais** (visualização apenas)

---

## 📊 Matriz de Permissões Simplificada

### Admin
```
✅ Ver tudo
✅ Criar tudo
✅ Editar tudo
✅ Deletar tudo
✅ Gerenciar usuários
✅ Ver credenciais
```

### Normal
```
✅ Ver: Dashboard, Contratos, Faturas, Telefonia, Histórico
✅ Criar: Contratos, Faturas
✅ Editar: Contratos*, Faturas*
❌ Deletar: Nada
❌ Credenciais: Sem acesso
* Apenas seus próprios registros
```

### Tercerizado
```
✅ Ver: Dashboard, Contratos, Faturas, Telefonia, Histórico, Credenciais
❌ Criar: Nada
❌ Editar: Nada
❌ Deletar: Nada
✅ Credenciais: Apenas visualizar
```

---

## 🔑 Rotas da API

### Verificação de Permissão

Todas as rotas agora verificam:

```python
# Exemplo: rota de credenciais
if usuario.role not in ["admin", "tercerizado"]:
    return HTTPException(403, "Sem permissão")
```

### Novas Rotas

#### `GET /dashboard/`
Retorna dados do dashboard (acessível a todos)

```json
{
  "usuario": "admin",
  "role": "admin",
  "total_contratos": 5,
  "total_faturas": 12,
  "total_numeros_telefonicos": 8
}
```

#### `GET /historico/`
Histórico de ações (acessível a todos)

Mesmos dados de `/logs/` mas com permissão ampla.

#### `GET /users/perfis`
Informações sobre os perfis (admin only)

```json
{
  "admin": {
    "nome": "Administrador (TI)",
    "descricao": "Acesso total ao sistema",
    "permissoes": {...}
  },
  "normal": {...},
  "tercerizado": {...}
}
```

---

## 🛡️ Testando as Permissões

### Via Frontend

**Teste 1: Verificar que Normal não vê Credenciais**
```
1. Login como usuário normal
2. Observe sidebar (Credenciais não aparece)
3. Console → Network → Tente GET /credenciais/ 
4. Resultado: 403 Forbidden
```

**Teste 2: Verificar que Tercerizado vê mas não edita Credenciais**
```
1. Login como tercerizado
2. Observe sidebar (Credenciais aparece)
3. Clique em Credenciais
4. Botão "Nova" não aparece
5. Tente deletar via console → 403 Forbidden
```

### Via cURL (Postman)

**Teste 3: Verificar permissão de API**
```bash
# 1. Obter token (tercerizado)
curl -X POST http://127.0.0.1:8001/token \
  -F "username=tercerizado_1" \
  -F "password=senha123"

# 2. Usar token para acessar credenciais
curl -X GET http://127.0.0.1:8001/credenciais/ \
  -H "Authorization: Bearer {token}"

# Resultado esperado: 200 OK com lista de credenciais

# 3. Tentar criar credencial (deve falhar)
curl -X POST http://127.0.0.1:8001/credenciais/ \
  -H "Authorization: Bearer {token}" \
  -F "nome_servico=Test" \
  -F "url_acesso=http://test.com" \
  -F "usuario=user" \
  -F "senha=pass"

# Resultado esperado: 403 Forbidden
```

---

## 🚨 Problemas Conhecidos e Soluções

### Problema 1: Tercerizado não consegue fazer login

**Solução:** O formulário de criação de usuário pode não permitir selecionar "tercerizado". 
- Use SQL direto para atualizar:
```sql
UPDATE users SET role = 'tercerizado' WHERE username = 'seu_usuario';
```

### Problema 2: Credenciais aparecem para Normal

**Solução:** Verifique o `role` no banco:
```sql
SELECT username, role FROM users;
```

### Problema 3: 403 Forbidden em rotas autorizadas

**Solução:** 
1. Verifique se o token é válido
2. Copie o token de novo do login
3. Verifique o `role` do usuário no banco de dados

---

## 📝 Checklist de Implementação

- ✅ Backend: Funções de verificação criadas
- ✅ Backend: Mapeamento de permissões criado
- ✅ Backend: Novas rotas `/dashboard/`, `/historico/`, `/users/perfis`
- ✅ Backend: Rotas existentes com verificação de permissão
- ✅ Frontend: Sidebar dinâmica por perfil
- ✅ Frontend: Credenciais com lógica condicional
- ✅ Frontend: Histórico acessível a todos
- ✅ Documentação: `SISTEMA_PERFIS.md` criado
- ✅ Documentação: `IMPLEMENTACAO_PERFIS.md` criado
- ✅ Testes: Backend operacional
- ✅ Testes: Frontend renderizando corretamente

---

## 📞 Arquivos Importantes

1. **SISTEMA_PERFIS.md** - Documentação completa do sistema
2. **IMPLEMENTACAO_PERFIS.md** - Detalhes técnicos da implementação
3. **backend/main.py** - Código backend com permissões
4. **frontend/src/App.jsx** - Interface com sidebar dinâmica

---

## 🎓 Próximas Melhorias Sugeridas

1. **Adicionar seletor de Role no Frontend**
   - Permite criar usuários com qualquer perfil via interface

2. **Dashboard Dinâmico**
   - Mostrar dados diferentes conforme o perfil

3. **Auditoria Detalhada**
   - Registrar quem tentou acessar o quê e quando

4. **Permissões Granulares**
   - Permitir criar perfis customizados

5. **2FA (Autenticação de Dois Fatores)**
   - Adicionar segurança extra para admin

---

**Status:** ✅ Sistema Operacional
**Data:** 28 de Janeiro de 2026
**Versão:** 2.5 Pro
