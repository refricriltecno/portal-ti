# 🔧 Correção: Conexão MongoDB no Render

## Problema Identificado
```
Exception: Não foi possível conectar ao MongoDB. 
connection closed (configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms)
```

## Causa Principal
O MongoDB Atlas está **bloqueando a conexão do Render** por não ter os IPs corretos na whitelist.

## ✅ Solução - Passo a Passo

### 1. Acessar MongoDB Atlas
1. Acesse [MongoDB Atlas](https://cloud.mongodb.com)
2. Faça login na sua conta
3. Selecione o cluster **Refricril**

### 2. Configurar Network Access (IP Whitelist)

#### Opção A - Permitir TODOS os IPs (Recomendado para Render)
1. No menu lateral, clique em **"Network Access"**
2. Clique em **"Add IP Address"**
3. Clique em **"ALLOW ACCESS FROM ANYWHERE"**
4. Confirme com **"0.0.0.0/0"**
5. Clique em **"Confirm"**

#### Opção B - Adicionar IPs específicos do Render
1. No menu lateral, clique em **"Network Access"**
2. Para cada um dos IPs abaixo, clique em **"Add IP Address"**:
   - `3.211.197.0/24`
   - `44.210.86.0/24`
   - `44.226.108.0/24`
   - `52.4.132.0/24`
   - `52.5.110.0/24`
   - `54.89.68.0/24`
   - `54.166.241.0/24`
   - `54.208.87.0/24`
   - `174.129.194.0/24`

### 3. Verificar String de Conexão

Sua string atual:
```
mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril
```

Certifique-se de que:
- ✅ O usuário `tecnologia_db_user` existe
- ✅ A senha `AdmRef212` está correta
- ✅ O usuário tem permissões de **readWrite** no banco `portal_ti`

### 4. Verificar Usuário do Banco

1. No MongoDB Atlas, clique em **"Database Access"**
2. Verifique se o usuário `tecnologia_db_user` existe
3. Clique em **"Edit"** no usuário
4. Em **"Database User Privileges"**, selecione:
   - **Built-in Role**: `readWriteAnyDatabase` ou
   - **Specific Privileges**: `readWrite` no banco `portal_ti`
5. Clique em **"Update User"**

### 5. Redeployar no Render

Após configurar o MongoDB Atlas:

```powershell
# Fazer commit das mudanças
git add .
git commit -m "fix: aumentar timeouts mongodb"
git push origin main
```

O Render vai fazer redeploy automaticamente.

## 🔍 Verificar Logs no Render

1. Acesse o [Dashboard do Render](https://dashboard.render.com)
2. Clique no seu Web Service
3. Vá em **"Logs"**
4. Procure por:
   - `✅ Conectado ao MongoDB Atlas` (sucesso)
   - `❌ Estratégia falhou` (falha)

## ⚡ Mudanças Aplicadas no Código

- ✅ Timeouts aumentados de 10s para 30s
- ✅ Adicionados `retryWrites` e `retryReads`
- ✅ Configurado pool de conexões (1-10)
- ✅ Adicionado `maxIdleTimeMS` para manter conexões ativas
- ✅ Tratamento de erro ao criar índices

## 🎯 Checklist Final

- [ ] Network Access configurado (0.0.0.0/0 ou IPs do Render)
- [ ] Usuário do banco com permissões corretas
- [ ] Senha verificada
- [ ] Código atualizado com novos timeouts
- [ ] Commit e push feitos
- [ ] Redeploy no Render concluído
- [ ] Logs verificados

## 📞 Se o Problema Persistir

### 1. Testar Conexão Localmente
```bash
cd backend
python test_mongodb_connection.py
```

### 2. Verificar Variável de Ambiente no Render
1. No Dashboard do Render, vá em **"Environment"**
2. Confirme que `DATABASE_URL` está definida
3. O valor deve ser: `mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril`

### 3. Logs Detalhados
Verifique no Render se aparece:
- `🔄 Tentando estratégia: TLS com retryWrites e timeouts longos...`
- `✅ Conectado ao MongoDB Atlas`

## 🚨 Erro Comum

**"No open ports detected"** - Este erro aparece DEPOIS do erro do MongoDB. 
Quando o MongoDB conectar, o servidor vai subir na porta correta.
