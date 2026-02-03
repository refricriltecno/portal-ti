import os
import shutil
import csv
import codecs
import re
from typing import List, Optional, Union
from datetime import date, datetime
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import certifi
from pymongo import ASCENDING
from bson.objectid import ObjectId
from pydantic import BaseModel, Field

# --- CONFIGURAÇÃO MONGODB ---
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")
UPLOAD_DIR = "uploads"
SECRET_KEY = "segredo_super_seguro_refricril"
ALGORITHM = "HS256"

# Cliente MongoDB
mongodb_client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None

async def connect_to_mongo():
    global mongodb_client, db
    try:
        mongodb_client = AsyncIOMotorClient(
            DATABASE_URL,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsCAFile=certifi.where()
        )
        # Test connection
        await mongodb_client.admin.command('ping')
        db = mongodb_client["portal_ti"]
        # Criar índices
        await db["users"].create_index([("username", ASCENDING)], unique=True)
        print("✅ Conectado ao MongoDB Atlas")
    except Exception as e:
        print(f"❌ Erro na conexão MongoDB: {e}")
        raise

async def close_mongo_connection():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("❌ Desconectado do MongoDB")

# --- SEGURANÇA ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# --- FUNÇÕES AUXILIARES ---
async def get_db():
    if db is None:
        raise HTTPException(status_code=500, detail="Banco de dados não conectado")
    return db

async def registrar_log(usuario: str, acao: str, alvo: str, alvo_id: str, detalhes: str):
    try:
        log_doc = {
            "usuario": usuario,
            "acao": acao,
            "alvo": alvo,
            "alvo_id": alvo_id,
            "detalhes": detalhes[:500],
            "data_hora": datetime.now()
        }
        await db["audit_logs"].insert_one(log_doc)
    except Exception as e:
        print(f"Erro Log: {e}")

def safe_float(v):
    if not v: return 0.0
    try:
        limpo = str(v).replace('R$', '').replace(' ', '')
        if ',' in limpo and '.' in limpo:
            limpo = limpo.replace('.', '').replace(',', '.')
        elif ',' in limpo:
            limpo = limpo.replace(',', '.')
        return float(limpo)
    except: 
        return 0.0

def safe_int(v):
    if not v: return 0
    try: 
        return int(float(v))
    except: 
        return 0

def safe_date(v):
    if not v: return None
    try: 
        return datetime.strptime(v, "%Y-%m-%d").date()
    except: 
        return None

# --- AUTH ---
async def get_current_user(token: str = Depends(oauth2_scheme), database = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: 
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user_doc = await database["users"].find_one({"username": username})
    if user_doc is None: 
        raise HTTPException(status_code=401)
    return user_doc

async def get_current_user_optional(token: str = Depends(oauth2_scheme), database = Depends(get_db)):
    """Retorna o usuário atual se autenticado, ou None se não autenticado"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: 
            return None
        user_doc = await database["users"].find_one({"username": username})
        return user_doc
    except JWTError:
        return None

# --- FUNÇÕES DE PERMISSÕES ---
def verificar_permissao(usuario: dict, rotas_permitidas: list):
    """Verifica se o usuário tem permissão para acessar a rota"""
    if usuario.get("role") not in rotas_permitidas:
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar este recurso")

def check_admin(usuario: dict):
    """Verifica se o usuário é admin"""
    if usuario.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso apenas para administradores")

def check_can_view_credentials(usuario: dict):
    """Verifica se o usuário pode visualizar credenciais"""
    if usuario.get("role") not in ["admin", "tercerizado"]:
        raise HTTPException(status_code=403, detail="Acesso apenas para administradores ou terceirizados")

# --- MAPEAMENTO DE PERMISSÕES POR RECURSO ---
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

# --- INICIALIZAÇÃO ---
app = FastAPI(title="Portal Gestão TI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- LIFECYCLE ---
@app.on_event("startup")
async def startup():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

# --- AUTH ROUTES ---
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), database = Depends(get_db)):
    user = await database["users"].find_one({"username": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")
    token = jwt.encode({"sub": user["username"], "role": user["role"]}, SECRET_KEY, algorithm=ALGORITHM)
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "role": user["role"], 
        "username": user["username"], 
        "foto_perfil": user.get("foto_perfil")
    }

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), current_user: Optional[dict] = Depends(get_current_user_optional), database = Depends(get_db)):
    user_count = await database["users"].count_documents({})
    
    if user_count > 0 and current_user is None:
        raise HTTPException(status_code=403, detail="Registro não permitido. Consulte o administrador.")
    
    if current_user and current_user.get("role") != 'admin':
        raise HTTPException(status_code=403, detail="Apenas admins podem registrar novos usuários")
    
    if await database["users"].find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Usuário já existe")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Usuário deve ter no mínimo 3 caracteres")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    
    hashed = pwd_context.hash(password)
    novo = {
        "username": username, 
        "hashed_password": hashed, 
        "role": "user", 
        "is_active": True,
        "foto_perfil": None
    }
    result = await database["users"].insert_one(novo)
    novo["_id"] = result.inserted_id
    
    if current_user:
        await registrar_log(current_user["username"], "CREATE", "USER", str(result.inserted_id), f"Novo usuário criado: {username}")
    
    token = jwt.encode({"sub": novo["username"], "role": novo["role"]}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": novo["role"], "username": novo["username"], "status": "usuário criado"}

# --- PERFIL DO USUÁRIO ---
@app.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": str(current_user.get("_id")),
        "username": current_user["username"], 
        "role": current_user["role"], 
        "is_active": current_user["is_active"], 
        "foto_perfil": current_user.get("foto_perfil")
    }

@app.put("/me/password")
async def change_password(current_password: str = Form(...), new_password: str = Form(...), current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    
    if not pwd_context.verify(current_password, current_user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    new_hashed = pwd_context.hash(new_password)
    await database["users"].update_one(
        {"_id": current_user["_id"]},
        {"$set": {"hashed_password": new_hashed}}
    )
    
    return {"status": "senha alterada com sucesso"}

@app.post("/me/foto")
async def upload_foto_perfil(foto: UploadFile = File(...), current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    if not foto.filename:
        raise HTTPException(status_code=400, detail="Arquivo não selecionado")
    
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if foto.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido. Use JPG, PNG, GIF ou WebP")
    
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    extensao = foto.filename.split('.')[-1].lower()
    nome_arquivo = f"FOTO_{current_user['_id']}_{ts}.{extensao}"
    caminho_pasta = os.path.join(UPLOAD_DIR, "perfis")
    os.makedirs(caminho_pasta, exist_ok=True)
    
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    with open(caminho_completo, "wb") as f:
        shutil.copyfileobj(foto.file, f)
    
    caminho_relativo = f"uploads/perfis/{nome_arquivo}"
    await database["users"].update_one(
        {"_id": current_user["_id"]},
        {"$set": {"foto_perfil": caminho_relativo}}
    )
    
    await registrar_log(current_user["username"], "UPDATE", "USER", str(current_user["_id"]), "Atualizou foto de perfil")
    
    return {"status": "sucesso", "foto_url": caminho_relativo}

# --- ROTAS DE USUÁRIOS E LOGS ---
@app.get("/users/perfis")
def get_perfis(current_user: dict = Depends(get_current_user)):
    """Retorna informações sobre os perfis disponíveis"""
    check_admin(current_user)
    
    perfis_info = {
        "admin": {
            "nome": "Administrador (TI)",
            "descricao": "Acesso total ao sistema",
            "permissoes": PERMISSOES
        },
        "normal": {
            "nome": "Usuário Normal",
            "descricao": "Acesso a dashboard, faturas, contratos, telefonia e histórico",
            "permissoes": {
                "dashboard": ["normal"],
                "faturas": ["normal"],
                "contratos": ["normal"],
                "telefonia": ["normal"],
                "historico": ["normal"]
            }
        },
        "tercerizado": {
            "nome": "Tercerizado",
            "descricao": "Acesso a dashboard, faturas, contratos, telefonia, histórico e credenciais",
            "permissoes": {
                "dashboard": ["tercerizado"],
                "faturas": ["tercerizado"],
                "contratos": ["tercerizado"],
                "telefonia": ["tercerizado"],
                "historico": ["tercerizado"],
                "credenciais": ["tercerizado"]
            }
        }
    }
    return perfis_info

@app.get("/users/")
async def list_users(current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    if current_user.get("role") != 'admin': 
        raise HTTPException(status_code=403)
    users = await database["users"].find({}).to_list(None)
    return [{"_id": str(u["_id"]), "username": u["username"], "role": u["role"], "is_active": u["is_active"]} for u in users]

@app.post("/users/")
async def create_user(username: str = Form(...), password: str = Form(...), role: str = Form("user"), current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    if current_user.get("role") != 'admin': 
        raise HTTPException(status_code=403)
    if await database["users"].find_one({"username": username}): 
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    hashed = pwd_context.hash(password)
    novo = {
        "username": username, 
        "hashed_password": hashed, 
        "role": role,
        "is_active": True,
        "foto_perfil": None
    }
    result = await database["users"].insert_one(novo)
    await registrar_log(current_user["username"], "CREATE", "USER", str(result.inserted_id), f"Novo usuário: {username}")
    return {"status": "criado"}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    if current_user.get("role") != 'admin': 
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar usuários")
    if user_id == str(current_user.get("_id")): 
        raise HTTPException(status_code=400, detail="Não pode deletar sua própria conta")
    
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    user = await database["users"].find_one({"_id": oid})
    if not user: 
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    username_deletado = user["username"]
    await database["users"].delete_one({"_id": oid})
    await registrar_log(current_user["username"], "DELETE", "USER", user_id, f"Usuário deletado: {username_deletado}")
    return {"status": "usuário deletado"}

@app.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str = Form(...), current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    """Atualiza o role/perfil de um usuário"""
    check_admin(current_user)
    if user_id == str(current_user.get("_id")): 
        raise HTTPException(status_code=400, detail="Não pode alterar seu próprio perfil")
    
    valid_roles = ['admin', 'normal', 'tercerizado']
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Deve ser um de: {', '.join(valid_roles)}")
    
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    user = await database["users"].find_one({"_id": oid})
    if not user: 
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    role_antigo = user["role"]
    await database["users"].update_one({"_id": oid}, {"$set": {"role": role}})
    await registrar_log(current_user["username"], "UPDATE", "USER", user_id, f"Perfil alterado: {role_antigo} → {role}")
    return {"status": "perfil atualizado", "novo_role": role}

@app.get("/logs/")
async def get_logs(current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    check_admin(current_user)
    logs = await database["audit_logs"].find({}).sort([("_id", -1)]).limit(100).to_list(None)
    return [{"_id": str(l["_id"]), **{k: v for k, v in l.items() if k != "_id"}} for l in logs]

@app.get("/historico/")
async def get_historico(current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    """Retorna o histórico de ações permitidas para o usuário"""
    verificar_permissao(current_user, PERMISSOES["historico"])
    
    query = {}
    if current_user.get("role") in ["normal", "tercerizado"]:
        query = {"alvo": {"$in": ["CONTRATO", "FATURA", "TELEFONIA"]}}
    
    logs = await database["audit_logs"].find(query).sort([("_id", -1)]).limit(100).to_list(None)
    return [{"_id": str(l["_id"]), **{k: v for k, v in l.items() if k != "_id"}} for l in logs]

# --- DASHBOARD ---
@app.get("/dashboard/")
async def get_dashboard(current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    """Retorna dados do dashboard para o usuário autenticado"""
    verificar_permissao(current_user, PERMISSOES["dashboard"])
    
    total_contratos = await database["contratos"].count_documents({"ativo": True})
    total_faturas = await database["faturas"].count_documents({})
    total_numeros = await database["numeros_telefonicos"].count_documents({"ativo": True})
    
    return {
        "usuario": current_user["username"],
        "role": current_user["role"],
        "total_contratos": total_contratos,
        "total_faturas": total_faturas,
        "total_numeros_telefonicos": total_numeros
    }

# --- CREDENCIAIS ---
@app.get("/credenciais/")
async def listar_credenciais(current_user: dict = Depends(get_current_user), database = Depends(get_db)):
    check_can_view_credentials(current_user)
    creds = await database["credenciais"].find({"ativo": True}).to_list(None)
    return [{"_id": str(c["_id"]), **{k: v for k, v in c.items() if k != "_id"}} for c in creds]

@app.post("/credenciais/")
async def criar_credencial(
    nome_servico: str = Form(...), url_acesso: str = Form(...),
    usuario: str = Form(...), senha: str = Form(...),
    descricao: Optional[str] = Form(None), email: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None), responsavel: Optional[str] = Form(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    check_admin(current_user)
    
    nova = {
        "nome_servico": nome_servico,
        "url_acesso": url_acesso,
        "usuario": usuario,
        "senha": senha,
        "descricao": descricao,
        "email": email,
        "telefone": telefone,
        "responsavel": responsavel,
        "ativo": True,
        "data_criacao": datetime.now(),
        "data_atualizacao": datetime.now()
    }
    result = await database["credenciais"].insert_one(nova)
    await registrar_log(current_user["username"], "CREATE", "CREDENCIAL", str(result.inserted_id), f"Nova credencial: {nome_servico}")
    return {"status": "criado", "id": str(result.inserted_id)}

@app.put("/credenciais/{id}")
async def editar_credencial(
    id: str,
    nome_servico: str = Form(...), url_acesso: str = Form(...),
    usuario: str = Form(...), senha: str = Form(...),
    descricao: Optional[str] = Form(None), email: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None), responsavel: Optional[str] = Form(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    check_admin(current_user)
    
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["credenciais"].find_one({"_id": oid})
    if not c: 
        raise HTTPException(status_code=404)
    
    update_data = {
        "nome_servico": nome_servico,
        "url_acesso": url_acesso,
        "usuario": usuario,
        "senha": senha,
        "descricao": descricao,
        "email": email,
        "telefone": telefone,
        "responsavel": responsavel,
        "data_atualizacao": datetime.now()
    }
    
    await database["credenciais"].update_one({"_id": oid}, {"$set": update_data})
    await registrar_log(current_user["username"], "UPDATE", "CREDENCIAL", id, f"Editou credencial: {nome_servico}")
    return {"status": "atualizado"}

@app.delete("/credenciais/{id}")
async def excluir_credencial(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    check_admin(current_user)
    
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["credenciais"].find_one({"_id": oid})
    if c:
        nome = c["nome_servico"]
        await database["credenciais"].delete_one({"_id": oid})
        await registrar_log(current_user["username"], "DELETE", "CREDENCIAL", id, f"Excluiu credencial: {nome}")
    return {"status": "deleted"}

# --- TELEFONIA ---
@app.get("/telefonia/")
async def listar_numeros(operadora: Optional[str] = None, mes: Optional[str] = None, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    verificar_permissao(current_user, PERMISSOES["telefonia"])
    query = {}
    if operadora and operadora != 'Todos':
        query["operadora"] = operadora
    if mes:
        query["mes_referencia"] = mes
    
    numeros = await database["numeros_telefonicos"].find(query).to_list(None)
    return [{"_id": str(n["_id"]), **{k: v for k, v in n.items() if k != "_id"}} for n in numeros]

@app.post("/telefonia/")
async def criar_numero(
    numero: str = Form(...), operadora: str = Form(...), valor: float = Form(...), 
    mes_referencia: str = Form(...), descricao: Optional[str] = Form(None),
    setor: Optional[str] = Form(None), filial: Optional[str] = Form(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    novo = {
        "numero": numero,
        "operadora": operadora,
        "valor": valor,
        "mes_referencia": mes_referencia,
        "descricao": descricao,
        "setor": setor,
        "filial": filial,
        "ativo": True,
        "data_upload": datetime.now().date()
    }
    result = await database["numeros_telefonicos"].insert_one(novo)
    await registrar_log(current_user["username"], "CREATE", "TELEFONIA", str(result.inserted_id), f"Adicionou {numero}")
    return {"status": "criado"}

@app.put("/telefonia/{id}")
async def editar_numero(
    id: str,
    numero: str = Form(...), operadora: str = Form(...), valor: float = Form(...), 
    mes_referencia: str = Form(...), descricao: Optional[str] = Form(None),
    setor: Optional[str] = Form(None), filial: Optional[str] = Form(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    n = await database["numeros_telefonicos"].find_one({"_id": oid})
    if not n: 
        raise HTTPException(status_code=404)
    
    update_data = {
        "numero": numero,
        "operadora": operadora,
        "valor": valor,
        "mes_referencia": mes_referencia,
        "descricao": descricao,
        "setor": setor,
        "filial": filial
    }
    
    await database["numeros_telefonicos"].update_one({"_id": oid}, {"$set": update_data})
    await registrar_log(current_user["username"], "UPDATE", "TELEFONIA", id, f"Editou {numero}")
    return {"status": "atualizado"}

@app.delete("/telefonia/{id}")
async def excluir_numero(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    n = await database["numeros_telefonicos"].find_one({"_id": oid})
    if n: 
        await database["numeros_telefonicos"].delete_one({"_id": oid})
    return {"status": "ok"}

# UPLOAD CSV TIM
@app.post("/telefonia/upload/tim")
async def upload_tim_csv(
    mes_referencia: str = Form(...), arquivo: UploadFile = File(...),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    await database["numeros_telefonicos"].delete_many({"operadora": "Tim", "mes_referencia": mes_referencia})
    conteudo = await arquivo.read()
    decoded = conteudo.decode('utf-8', errors='replace').splitlines()
    reader = csv.reader(decoded)
    count = 0
    next(reader, None)
    
    docs_to_insert = []
    for row in reader:
        if len(row) >= 3:
            try:
                num = row[0].strip()
                if not num.isdigit(): 
                    continue 
                docs_to_insert.append({
                    "numero": num,
                    "operadora": "Tim",
                    "descricao": row[1].strip(),
                    "valor": safe_float(row[2]),
                    "mes_referencia": mes_referencia,
                    "setor": "Indefinido",
                    "filial": "Indefinido",
                    "ativo": True,
                    "data_upload": datetime.now().date()
                })
                count += 1
            except: 
                continue
    
    if docs_to_insert:
        await database["numeros_telefonicos"].insert_many(docs_to_insert)
    
    await registrar_log(current_user["username"], "UPLOAD", "TIM", "0", f"Importou {count} linhas")
    return {"status": "sucesso", "linhas_importadas": count}

# UPLOAD CSV INVENTÁRIO
@app.post("/telefonia/upload/inventario")
async def upload_inventario_csv(
    mes_referencia: str = Form(...),
    arquivo: UploadFile = File(...),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    await database["numeros_telefonicos"].delete_many({"mes_referencia": mes_referencia})
    
    conteudo = await arquivo.read()
    decoded = conteudo.decode('utf-8', errors='replace').splitlines()
    reader = csv.reader(decoded, delimiter=';')
    
    count = 0
    header = next(reader, None)
    
    docs_to_insert = []
    for row in reader:
        if len(row) >= 17:
            try:
                raw_num = row[0]
                num = re.sub(r'\D', '', raw_num)
                
                if not num: 
                    continue

                filial = row[4].strip() if row[4].strip() else "Indefinido"
                setor = row[5].strip() if row[5].strip() else "Indefinido"
                operadora = row[11].strip() if row[11].strip() else "Desconhecida"
                valor = safe_float(row[16])

                docs_to_insert.append({
                    "numero": num,
                    "operadora": operadora,
                    "descricao": "Importado via Inventário",
                    "valor": valor,
                    "mes_referencia": mes_referencia,
                    "filial": filial,
                    "setor": setor,
                    "ativo": True,
                    "data_upload": datetime.now().date()
                })
                count += 1
            except Exception as e: 
                print(f"Erro linha: {e}")
    
    if docs_to_insert:
        await database["numeros_telefonicos"].insert_many(docs_to_insert)
    
    await registrar_log(current_user["username"], "UPLOAD", "INVENTARIO", "0", f"Importou {count} linhas de inventário")
    return {"status": "sucesso", "linhas_importadas": count}

# --- CONTRATOS ---
@app.get("/contratos/")
async def listar_contratos(database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    verificar_permissao(current_user, PERMISSOES["contratos"])
    contratos = await database["contratos"].find({"ativo": True}).sort([("_id", -1)]).to_list(None)
    return [{"_id": str(c["_id"]), **{k: v for k, v in c.items() if k != "_id"}} for c in contratos]

@app.post("/contratos/")
async def criar_contrato(
    nome_amigavel: str = Form(...), filial: str = Form(...), 
    fornecedor_razao: str = Form(...), cnpj_fornecedor: str = Form(...),
    fornecedor2_razao: Optional[str] = Form(None), cnpj_fornecedor2: Optional[str] = Form(None),
    centro_custo: str = Form(...), tipo: str = Form(...),
    valor_total: Union[str, float] = Form(0), tempo_contrato_meses: Union[str, int] = Form(0),
    data_inicio_cobranca: Optional[str] = Form(None), dia_vencimento: Union[str, int] = Form(0),
    identificadores: Optional[str] = Form(None), info_adicional: Optional[str] = Form(None),
    tem_rateio: Union[str, bool] = Form(False), empresas_rateio: Optional[str] = Form(None),
    arquivo: UploadFile = File(None), database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    path = None
    if arquivo:
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        name = f"CONTRATO_{ts}_{arquivo.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as b: 
            shutil.copyfileobj(arquivo.file, b)
        path = f"uploads/{name}"

    if isinstance(tem_rateio, str): 
        tem_rateio = tem_rateio.lower() in ['true', '1']

    novo = {
        "nome_amigavel": nome_amigavel,
        "filial": filial,
        "fornecedor_razao": fornecedor_razao,
        "cnpj_fornecedor": cnpj_fornecedor,
        "fornecedor2_razao": fornecedor2_razao,
        "cnpj_fornecedor2": cnpj_fornecedor2,
        "centro_custo": centro_custo,
        "tipo": tipo,
        "valor_total": safe_float(valor_total),
        "tempo_contrato_meses": safe_int(tempo_contrato_meses),
        "data_inicio_cobranca": safe_date(data_inicio_cobranca),
        "dia_vencimento": safe_int(dia_vencimento),
        "identificadores": identificadores,
        "info_adicional": info_adicional,
        "tem_rateio": tem_rateio,
        "empresas_rateio": empresas_rateio,
        "caminho_arquivo": path,
        "ativo": True
    }
    result = await database["contratos"].insert_one(novo)
    await registrar_log(current_user["username"], "CREATE", "CONTRATO", str(result.inserted_id), f"Criou contrato {nome_amigavel}")
    return {"status": "criado"}

@app.put("/contratos/{id}")
async def editar_contrato(
    id: str, nome_amigavel: str = Form(...), filial: str = Form(...), 
    fornecedor_razao: str = Form(...), cnpj_fornecedor: str = Form(...),
    fornecedor2_razao: Optional[str] = Form(None), cnpj_fornecedor2: Optional[str] = Form(None),
    centro_custo: str = Form(...), tipo: str = Form(...),
    valor_total: Union[str, float] = Form(0), tempo_contrato_meses: Union[str, int] = Form(0),
    data_inicio_cobranca: Optional[str] = Form(None), dia_vencimento: Union[str, int] = Form(0),
    identificadores: Optional[str] = Form(None), info_adicional: Optional[str] = Form(None),
    tem_rateio: Union[str, bool] = Form(False), empresas_rateio: Optional[str] = Form(None),
    arquivo: UploadFile = File(None), database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["contratos"].find_one({"_id": oid})
    if not c: 
        raise HTTPException(status_code=404)
    
    alteracoes = []
    novo_valor = safe_float(valor_total)
    novo_meses = safe_int(tempo_contrato_meses)
    
    if isinstance(tem_rateio, str): 
        tem_rateio = tem_rateio.lower() in ['true', '1']
    
    if c.get("nome_amigavel") != nome_amigavel: 
        alteracoes.append(f"nome: {c.get('nome_amigavel')}→{nome_amigavel}")
    if c.get("valor_total") != novo_valor: 
        alteracoes.append(f"valor: R${c.get('valor_total', 0):.2f}→R${novo_valor:.2f}")
    if c.get("tempo_contrato_meses") != novo_meses: 
        alteracoes.append(f"meses: {c.get('tempo_contrato_meses')}→{novo_meses}")
    if c.get("fornecedor_razao") != fornecedor_razao: 
        alteracoes.append(f"fornecedor: {c.get('fornecedor_razao')}→{fornecedor_razao}")
    if c.get("filial") != filial: 
        alteracoes.append("filial alterada")
    if c.get("centro_custo") != centro_custo: 
        alteracoes.append("centro de custo alterado")
    if arquivo: 
        alteracoes.append("arquivo atualizado")
    
    update_data = {
        "nome_amigavel": nome_amigavel,
        "filial": filial,
        "fornecedor_razao": fornecedor_razao,
        "cnpj_fornecedor": cnpj_fornecedor,
        "fornecedor2_razao": fornecedor2_razao,
        "cnpj_fornecedor2": cnpj_fornecedor2,
        "centro_custo": centro_custo,
        "tipo": tipo,
        "valor_total": novo_valor,
        "tempo_contrato_meses": novo_meses,
        "data_inicio_cobranca": safe_date(data_inicio_cobranca),
        "dia_vencimento": safe_int(dia_vencimento),
        "identificadores": identificadores,
        "info_adicional": info_adicional,
        "tem_rateio": tem_rateio,
        "empresas_rateio": empresas_rateio
    }
    
    if arquivo:
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        name = f"CONTRATO_{id}_{ts}_{arquivo.filename.replace(' ', '_')}"
        path = f"uploads/{name}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as b: 
            shutil.copyfileobj(arquivo.file, b)
        update_data["caminho_arquivo"] = path
    
    await database["contratos"].update_one({"_id": oid}, {"$set": update_data})
    detalhes_log = f"{nome_amigavel}: {', '.join(alteracoes)}" if alteracoes else f"{nome_amigavel} editado (sem alterações)"
    await registrar_log(current_user["username"], "UPDATE", "CONTRATO", id, detalhes_log)
    return {"status": "atualizado"}

@app.delete("/contratos/{id}")
async def excluir_contrato(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["contratos"].find_one({"_id": oid})
    if c:
        nome = c.get("nome_amigavel")
        await database["contratos"].delete_one({"_id": oid})
        await registrar_log(current_user["username"], "DELETE", "CONTRATO", id, f"Excluiu {nome}")
    return {"status": "deleted"}

@app.put("/contratos/{id}/inativar")
async def inativar_contrato(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["contratos"].find_one({"_id": oid})
    if not c: 
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    nome = c.get("nome_amigavel")
    await database["contratos"].update_one({"_id": oid}, {"$set": {"ativo": False}})
    await registrar_log(current_user["username"], "INATIVAR", "CONTRATO", id, f"Inativou contrato: {nome}")
    return {"status": "inativado", "mensagem": f"Contrato '{nome}' inativado com sucesso"}

@app.put("/contratos/{id}/ativar")
async def ativar_contrato(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    c = await database["contratos"].find_one({"_id": oid})
    if not c: 
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    nome = c.get("nome_amigavel")
    await database["contratos"].update_one({"_id": oid}, {"$set": {"ativo": True}})
    await registrar_log(current_user["username"], "ATIVAR", "CONTRATO", id, f"Ativou contrato: {nome}")
    return {"status": "ativado", "mensagem": f"Contrato '{nome}' ativado com sucesso"}

# --- FATURAS ---
@app.get("/faturas/")
async def listar_faturas(database = Depends(get_db), current_user: dict = Depends(get_current_user)): 
    verificar_permissao(current_user, PERMISSOES["faturas"])
    faturas = await database["faturas"].find({"ativo": True}).to_list(None)
    return [{"_id": str(f["_id"]), **{k: v for k, v in f.items() if k != "_id"}} for f in faturas]

@app.post("/faturas/")
async def lancar_fatura(
    contrato_id: Union[str, int] = Form(...), mes_referencia: str = Form(...), valor: Union[str, float] = Form(...),
    data_vencimento: Optional[str] = Form(None), numero_circuito: Optional[str] = Form(None),
    status: str = Form("Pendente envio do boleto"), desconto: Union[str, float] = Form(0.0), acrescimo: Union[str, float] = Form(0.0),
    observacoes: Optional[str] = Form(None), 
    arquivo: UploadFile = File(...), 
    arquivo_nf: UploadFile = File(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    path_boleto = f"uploads/BOLETO_{contrato_id}_{ts}_{arquivo.filename.replace(' ', '_')}"
    with open(os.path.join(UPLOAD_DIR, os.path.basename(path_boleto)), "wb") as b: 
        shutil.copyfileobj(arquivo.file, b)
    
    path_nf = None
    if arquivo_nf:
        path_nf = f"uploads/NF_{contrato_id}_{ts}_{arquivo_nf.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path_nf)), "wb") as b: 
            shutil.copyfileobj(arquivo_nf.file, b)

    v_val = safe_float(valor)
    v_desc = safe_float(desconto)
    v_acre = safe_float(acrescimo)
    
    nova = {
        "contrato_id": str(contrato_id),
        "mes_referencia": mes_referencia,
        "valor": v_val,
        "valor_ajustado": v_val + v_acre - v_desc,
        "desconto": v_desc,
        "acrescimo": v_acre,
        "data_vencimento": safe_date(data_vencimento),
        "numero_circuito": numero_circuito,
        "status": status,
        "observacoes": observacoes,
        "caminho_arquivo": path_boleto,
        "caminho_nf": path_nf,
        "data_upload": datetime.now().date(),
        "ativo": True
    }
    result = await database["faturas"].insert_one(nova)
    await registrar_log(current_user["username"], "CREATE", "FATURA", str(result.inserted_id), f"Lançou fatura {mes_referencia}")
    return {"status": "sucesso"}

@app.put("/faturas/{id}")
async def editar_fatura(
    id: str, contrato_id: Union[str, int] = Form(...), mes_referencia: str = Form(...), valor: Union[str, float] = Form(...),
    data_vencimento: Optional[str] = Form(None), numero_circuito: Optional[str] = Form(None),
    desconto: Union[str, float] = Form(0.0), acrescimo: Union[str, float] = Form(0.0),
    observacoes: Optional[str] = Form(None), 
    arquivo: UploadFile = File(None), 
    arquivo_nf: UploadFile = File(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    f = await database["faturas"].find_one({"_id": oid})
    if not f: 
        raise HTTPException(status_code=404)

    alteracoes = []
    v_val = safe_float(valor)
    v_desc = safe_float(desconto)
    v_acre = safe_float(acrescimo)
    novo_contrato_id = str(contrato_id)
    
    if f.get("contrato_id") != novo_contrato_id: 
        alteracoes.append(f"contrato_id: {f.get('contrato_id')}→{novo_contrato_id}")
    if f.get("mes_referencia") != mes_referencia: 
        alteracoes.append(f"mês: {f.get('mes_referencia')}→{mes_referencia}")
    if f.get("valor") != v_val: 
        alteracoes.append(f"valor: R${f.get('valor', 0):.2f}→R${v_val:.2f}")
    if f.get("desconto") != v_desc: 
        alteracoes.append(f"desconto: R${f.get('desconto', 0):.2f}→R${v_desc:.2f}")
    if f.get("acrescimo") != v_acre: 
        alteracoes.append(f"acréscimo: R${f.get('acrescimo', 0):.2f}→R${v_acre:.2f}")
    if data_vencimento and f.get("data_vencimento") != safe_date(data_vencimento): 
        alteracoes.append(f"vencimento: {f.get('data_vencimento')}→{data_vencimento}")
    if numero_circuito and f.get("numero_circuito") != numero_circuito: 
        alteracoes.append(f"circuito: {f.get('numero_circuito')}→{numero_circuito}")
    if observacoes and f.get("observacoes") != observacoes: 
        alteracoes.append("observações alteradas")
    if arquivo: 
        alteracoes.append("boleto atualizado")
    if arquivo_nf: 
        alteracoes.append("NF atualizada")

    update_data = {
        "contrato_id": novo_contrato_id,
        "mes_referencia": mes_referencia,
        "valor": v_val,
        "data_vencimento": safe_date(data_vencimento),
        "numero_circuito": numero_circuito,
        "desconto": v_desc,
        "acrescimo": v_acre,
        "valor_ajustado": v_val + v_acre - v_desc,
        "observacoes": observacoes
    }

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    if arquivo:
        path = f"uploads/BOLETO_{contrato_id}_{ts}_{arquivo.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path)), "wb") as b: 
            shutil.copyfileobj(arquivo.file, b)
        update_data["caminho_arquivo"] = path
    if arquivo_nf:
        path = f"uploads/NF_{contrato_id}_{ts}_{arquivo_nf.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path)), "wb") as b: 
            shutil.copyfileobj(arquivo_nf.file, b)
        update_data["caminho_nf"] = path

    await database["faturas"].update_one({"_id": oid}, {"$set": update_data})
    detalhes_log = f"Fatura #{id}: {', '.join(alteracoes)}" if alteracoes else f"Fatura #{id} editada (sem alterações)"
    await registrar_log(current_user["username"], "UPDATE", "FATURA", id, detalhes_log)
    return {"status": "atualizado"}

@app.put("/faturas/{id}/status")
async def atualizar_status(
    id: str, status: str = Form(...), data_pagamento: Optional[str] = Form(None), observacoes: Optional[str] = Form(None),
    database = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    f = await database["faturas"].find_one({"_id": oid})
    if f:
        status_anterior = f.get("status")
        detalhes = f"Fatura #{id}: {status_anterior}→{status}"
        if data_pagamento: 
            detalhes += f", pago em {data_pagamento}"
        if observacoes: 
            detalhes += f", obs: {observacoes[:50]}"
        
        update_data = {"status": status}
        if data_pagamento: 
            update_data["data_pagamento"] = safe_date(data_pagamento)
        if observacoes: 
            update_data["observacoes"] = observacoes
        
        await database["faturas"].update_one({"_id": oid}, {"$set": update_data})
        await registrar_log(current_user["username"], "UPDATE", "FATURA", id, detalhes)
    return {"status": "ok"}

@app.put("/faturas/{id}/inativar")
async def inativar_fatura(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    f = await database["faturas"].find_one({"_id": oid})
    if not f: 
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    
    await database["faturas"].update_one({"_id": oid}, {"$set": {"ativo": False}})
    await registrar_log(current_user["username"], "INATIVAR", "FATURA", id, f"Inativou fatura #{id}")
    return {"status": "inativado", "mensagem": f"Fatura #{id} inativada com sucesso"}

@app.put("/faturas/{id}/ativar")
async def ativar_fatura(id: str, database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    f = await database["faturas"].find_one({"_id": oid})
    if not f: 
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    
    await database["faturas"].update_one({"_id": oid}, {"$set": {"ativo": True}})
    await registrar_log(current_user["username"], "ATIVAR", "FATURA", id, f"Ativou fatura #{id}")
    return {"status": "ativado", "mensagem": f"Fatura #{id} ativada com sucesso"}

@app.get("/dashboard/stats")
async def get_stats(database = Depends(get_db), current_user: dict = Depends(get_current_user)):
    faturas = await database["faturas"].find({}).to_list(None)
    contratos = await database["contratos"].find({"ativo": True}).to_list(None)
    previsao = sum([c.get("valor_total", 0) / (c.get("tempo_contrato_meses", 1) if c.get("tempo_contrato_meses") else 1) for c in contratos])
    
    faturas_pendentes = sum(1 for f in faturas if f.get("status") == "Pendente")
    valor_pendente = sum(f.get("valor_ajustado", 0) for f in faturas if f.get("status") == "Pendente")
    valor_pago = sum(f.get("valor_ajustado", 0) for f in faturas if f.get("status") == "Pago")
    
    return {
        "contratos_ativos": len(contratos),
        "faturas_pendentes": faturas_pendentes,
        "total_faturas": len(faturas),
        "valor_contratos_mensal": previsao,
        "valor_pendente": valor_pendente,
        "valor_pago": valor_pago
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
