# 🚀 Guia de Migração para Render

## Status Atual
- **Banco Origem**: `10.1.1.248:5432/portal_ti` (Rede Interna)
- **Banco Destino**: Render PostgreSQL (Externo/Cloud)
- **Objetivo**: Permitir acesso do terceiro fora da rede corporativa

## Credenciais Render

```
Host: dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com
Port: 5432
Database: portal_ti_db
User: portal_ti_db_user
Password: EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9
```

## Pré-Requisitos

### 1. Verificar PostgreSQL Client Tools
O Windows precisa ter `pg_dump` e `psql` instalados:

```powershell
pg_dump --version
psql --version
```

Se não estiverem instalados:
- Baixe em: https://www.postgresql.org/download/windows/
- Ou instale pelo WSL: `sudo apt-get install postgresql-client`

### 2. Verificar Conectividade

```powershell
# Testar conexão ao banco atual
psql -h 10.1.1.248 -U portal_user -d portal_ti -c "SELECT version();"

# Testar conexão ao Render (pode levar alguns segundos)
psql -h dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com -U portal_ti_db_user -d portal_ti_db -c "SELECT version();"
```

## Método 1: Usando pg_dump/psql (Recomendado)

### Opção A: Script Python Automático
```powershell
cd backend
python migrar_para_render.py
```

O script irá:
1. ✅ Testar conexões
2. ✅ Fazer dump do banco atual
3. ✅ Restaurar no Render
4. ✅ Verificar integridade dos dados

### Opção B: Manualmente (passo a passo)

#### 1. Fazer backup do banco atual
```powershell
$env:PGPASSWORD = "Adm@Ref212"
pg_dump -h 10.1.1.248 -U portal_user -d portal_ti --format=plain > backup_portal_ti.sql
```

#### 2. Restaurar no Render
```powershell
$env:PGPASSWORD = "EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9"
psql -h dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com -U portal_ti_db_user -d portal_ti_db < backup_portal_ti.sql
```

## Método 2: Usar Python (Alternativo)

Se pg_dump/psql não estiverem disponíveis:

```powershell
cd backend
python migrar_alternativo.py
```

**⚠️ Nota**: Este método é mais lento mas não requer PostgreSQL Client Tools.

## Atualizar Aplicação após Migração

### 1. Atualizar `backend/main.py`

Altere a variável `DATABASE_URL`:

```python
# De:
DATABASE_URL = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"

# Para:
DATABASE_URL = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"
```

### 2. Ou usar variável de ambiente (Melhor para produção)

```powershell
# No PowerShell
$env:DATABASE_URL = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"

# Ou criar um arquivo .env no backend/
echo "DATABASE_URL=postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db" > backend/.env
```

### 3. Reiniciar o servidor Python

```powershell
# Mate o processo anterior (Ctrl+C)
# Depois execute novamente:
cd backend
python main.py
```

## Verificação Pós-Migração

### 1. Verificar se os dados foram migrados
```powershell
# Conectar ao Render e verificar tabelas
$env:PGPASSWORD = "EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9"
psql -h dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com -U portal_ti_db_user -d portal_ti_db -c "\dt"
```

### 2. Contar registros em cada tabela
```sql
SELECT tablename, 
       (SELECT count(*) FROM "public"."users") as users_count,
       (SELECT count(*) FROM "public"."contratos") as contratos_count,
       (SELECT count(*) FROM "public"."faturas") as faturas_count
FROM pg_tables WHERE schemaname = 'public';
```

### 3. Teste de API
```powershell
# Testar um endpoint
Invoke-RestMethod -Uri "http://localhost:8001/contratos" -Method Get
```

## Solução de Problemas

### ❌ "connection refused" ao banco Render
- Verificar credenciais no script
- Verificar se o banco Render está ativo
- Pode levar alguns segundos para inicializar

### ❌ "pg_dump not found"
- Instalar PostgreSQL Client Tools
- Ou usar `migrar_alternativo.py`

### ❌ "permission denied" no arquivo backup
- Verificar permissões da pasta `backend/`
- Tentar em uma pasta diferente (`C:\Temp\`)

### ❌ Dados incompletos após migração
- Verificar se o script foi executado completamente
- Verificar logs do banco Render
- Fazer rollback: usar backup salvo em `.sql`

## Segurança

⚠️ **IMPORTANTE**: As credenciais estão visíveis no script!

Após migração bem-sucedida, considere:
1. Mudar a senha no Render (Se o banco permitir)
2. Usar variáveis de ambiente ao invés de hardcoded
3. Guardar as credenciais em local seguro
4. Não fazer commit de `migrar_para_render.py` com credenciais no Git

## Próximas Etapas

1. ✅ Executar migração (script automático)
2. ✅ Atualizar DATABASE_URL em main.py
3. ✅ Reiniciar servidor FastAPI
4. ✅ Testar acesso do terceiro (teste de conectividade)
5. ✅ Monitorar logs do servidor
6. ✅ Considerar fazer backup periódico do Render

## Documentação de Referência

- [Render PostgreSQL Docs](https://render.com/docs/databases)
- [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)
- [PostgreSQL psql](https://www.postgresql.org/docs/current/app-psql.html)
