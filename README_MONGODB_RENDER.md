# 🚀 Portal TI - MongoDB Atlas + Render

## ⚡ Quick Start

### Opção 1: Deploy Automático (Recomendado)

```bash
# Windows
.\deploy_render.ps1

# Linux/Mac
bash deploy_render.sh
```

### Opção 2: Manual

#### 1. Preparar código
```bash
cp backend/main_mongodb.py backend/main.py
git add .
git commit -m "Migração MongoDB Atlas"
git push origin main
```

#### 2. Criar Web Service no Render
- Acesse: https://render.com
- Conecte GitHub
- Build: `pip install -r backend/requirements.txt`
- Start: `cd backend && python -m uvicorn main_mongodb:app --host 0.0.0.0 --port 8001`

#### 3. Variáveis de Ambiente
```
DATABASE_URL=mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril
SECRET_KEY=segredo_super_seguro_refricril
ALGORITHM=HS256
PYTHONUNBUFFERED=1
```

---

## 📋 O Que Mudou

| Aspecto | Antes | Depois |
|--------|-------|--------|
| **Banco** | PostgreSQL | MongoDB Atlas |
| **Driver** | SQLAlchemy | Motor (async) |
| **Host** | 10.1.1.248 | Cloud Atlas |
| **Platform** | Local | Render |

---

## ✅ Testes

### Teste Local
```bash
cd backend
python test_mongodb_connection.py
```

Esperado:
```
✅ Conexão bem-sucedida!
✅ TUDO FUNCIONANDO!
```

### Teste em Produção (após deploy)
```bash
curl https://seu-app.onrender.com/docs
```

---

## 📚 Documentação

- **SETUP_MONGODB_RENDER.md** - Guia completo com checklists
- **MIGRACAO_MONGODB_RENDER.md** - Detalhes técnicos da migração
- **render.yaml** - Configuração de deploy YAML

---

## 🔧 Troubleshooting Rápido

### "Connection refused"
```bash
# Verificar conexão
python backend/test_mongodb_connection.py
```

### "Module not found"
```bash
pip install -r backend/requirements.txt
```

### "Cannot find main.py"
```bash
# Ensure main_mongodb.py is renamed to main.py
cp backend/main_mongodb.py backend/main.py
```

---

## 📊 Estrutura

```
portal_ti/
├── backend/
│   ├── main_mongodb.py          ← Produção
│   ├── main_postgres_backup.py  ← Backup
│   ├── requirements.txt         ← Dependências
│   ├── .env                     ← Config
│   └── test_mongodb_connection.py
├── frontend/
├── SETUP_MONGODB_RENDER.md      ← Guia completo
├── MIGRACAO_MONGODB_RENDER.md   ← Detalhes técnicos
├── deploy_render.ps1            ← Script Windows
├── deploy_render.sh             ← Script Linux/Mac
└── render.yaml                  ← Config deploy
```

---

## ✨ Status

- ✅ Backend refatorado
- ✅ MongoDB Atlas configurado
- ✅ Conexão testada e validada
- ✅ Documentação completa
- ✅ Scripts de deploy criados
- ⏳ **Pronto para: Deploy no Render**

---

## 🎯 Próximos Passos

1. Executar teste de conexão:
   ```bash
   python backend/test_mongodb_connection.py
   ```

2. Fazer commit e push:
   ```bash
   git push origin main
   ```

3. Criar Web Service no Render:
   - https://render.com
   - New → Web Service
   - Conecte GitHub

4. Adicionar variáveis de ambiente no Render

5. Deploy automático iniciará

---

## 📞 Ajuda Rápida

**Teste local não passa?**
- Verificar internet
- Verificar IP na lista branca do MongoDB Atlas
- Executar: `python backend/test_mongodb_connection.py`

**Deploy no Render falha?**
- Verificar Build Command output nos logs
- Verificar variáveis de ambiente
- Verificar Python version (3.9+)

---

**Data**: 3 de fevereiro de 2026  
**Status**: ✅ Pronto para produção
