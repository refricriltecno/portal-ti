# 🚀 Guia de Migração para MongoDB Atlas + Render

## 📋 Resumo da Migração

Seu sistema foi migrado de **PostgreSQL** para **MongoDB Atlas** e está pronto para rodar no **Render**.

### Mudanças Principais:

1. ✅ **Banco de Dados**: PostgreSQL → MongoDB Atlas
2. ✅ **String de Conexão**: `mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril`
3. ✅ **Dependências**: SQLAlchemy → Motor (async MongoDB driver)
4. ✅ **Modelos**: SQLAlchemy ORM → Pydantic + MongoDB Collections
5. ✅ **Arquivo Principal**: `main_mongodb.py` (ready for production)

---

## 🔧 Configuração Local

### 1. Instalar Dependências

```bash
cd backend
pip install -r requirements.txt
```

### 2. Arquivo .env

```
DATABASE_URL=mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril
SECRET_KEY=segredo_super_seguro_refricril
ALGORITHM=HS256
UPLOAD_DIR=uploads
```

### 3. Rodar Localmente

```bash
# Substituir main.py pelo main_mongodb.py
cp main_mongodb.py main.py

# Executar
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🌐 Deploy no Render

### 1. Fazer Push do Código para GitHub

```bash
git add backend/
git commit -m "Migração para MongoDB Atlas"
git push origin main
```

### 2. Criar Serviço Web no Render

1. Acesse [render.com](https://render.com)
2. Clique em **New** → **Web Service**
3. Selecione seu repositório GitHub
4. Configure:

```
Nome: portal-ti-backend
Ambiente: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && python -m uvicorn main_mongodb:app --host 0.0.0.0 --port 8001
```

### 3. Variáveis de Ambiente

No painel do Render, adicione as variáveis de ambiente:

```
DATABASE_URL=mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril
SECRET_KEY=segredo_super_seguro_refricril
ALGORITHM=HS256
UPLOAD_DIR=uploads
```

### 4. Deploy

O Render fará deploy automaticamente quando você fazer push.

---

## ✅ Verificar Conexão

Após o deploy, teste a conexão:

```bash
curl https://seu-app.onrender.com/dashboard/ \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

## 📊 Estrutura do MongoDB

As coleções criadas automaticamente:

```
portal_ti/
  ├── users
  ├── audit_logs
  ├── credenciais
  ├── numeros_telefonicos
  ├── contratos
  └── faturas
```

---

## 🔄 Migração de Dados (Opcional)

Se você tem dados no PostgreSQL e quer migrar:

### Script de Migração

```python
# script_migracao_pg_mongo.py
import psycopg2
from motor.motor_asyncio import AsyncClient
import asyncio

async def migrar():
    # Conectar PostgreSQL
    pg_conn = psycopg2.connect(
        host="seu_host",
        user="seu_user",
        password="sua_senha",
        database="portal_ti"
    )
    
    # Conectar MongoDB
    mongo_client = AsyncClient("mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")
    db = mongo_client["portal_ti"]
    
    # Migrar dados...
    # (Implementar conforme necessário)
    
    pg_conn.close()
    mongo_client.close()

asyncio.run(migrar())
```

---

## 🛠️ Troubleshooting

### Erro: "Connection refused"
- Verificar string de conexão do MongoDB
- Verificar se o IP está na lista branca do MongoDB Atlas

### Erro: "Module not found"
- Executar: `pip install -r requirements.txt`
- Verificar Python 3.9+

### Uploads não aparecem
- Render não persiste arquivos no `/uploads` por padrão
- Considere usar S3 ou similar para produção

---

## 📞 Referências

- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [Render.com Docs](https://render.com/docs)
- [FastAPI + Motor](https://fastapi.tiangolo.com/)

---

## ✨ Próximos Passos

1. ✅ Deploy no Render
2. ✅ Testar todas as rotas
3. ✅ Migrar dados (se existentes)
4. ✅ Configurar SSL/HTTPS (automático no Render)
5. ✅ Monitorar logs em tempo real

---

**Status**: ✅ Pronto para produção
**Data**: 3 de fevereiro de 2026
