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
from motor.motor_asyncio import AsyncClient, AsyncDatabase
from pymongo import ASCENDING
from bson.objectid import ObjectId
from pydantic import BaseModel, Field

# --- CONFIGURAÇÃO MONGODB ---
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")
UPLOAD_DIR = "uploads"
SECRET_KEY = "segredo_super_seguro_refricril"
ALGORITHM = "HS256"

# Cliente MongoDB
mongodb_client: Optional[AsyncClient] = None
db: Optional[AsyncDatabase] = None

async def connect_to_mongo():
    global mongodb_client, db
    mongodb_client = AsyncClient(DATABASE_URL)
    db = mongodb_client["portal_ti"]
    # Criar índices
    await db["users"].create_index([("username", ASCENDING)], unique=True)
    print("✅ Conectado ao MongoDB Atlas")

async def close_mongo_connection():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("❌ Desconectado do MongoDB")

# --- SEGURANÇA ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# --- MODELOS PYDANTIC ---
class UserDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    username: str
    hashed_password: str
    role: str = "user"
    is_active: bool = True
    foto_perfil: Optional[str] = None
    
    class Config:
        populate_by_name = True

class AuditLogDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    usuario: str
    acao: str
    alvo: str
    alvo_id: Optional[str] = None
    detalhes: str
    data_hora: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True

class NumeroTelefonicoDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    numero: str
    operadora: str
    descricao: Optional[str] = None
    valor: float = 0.0
    mes_referencia: str
    setor: Optional[str] = None
    filial: Optional[str] = None
    ativo: bool = True
    data_upload: date = Field(default_factory=datetime.now().date)
    
    class Config:
        populate_by_name = True

class ContratoDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    nome_amigavel: str
    filial: str
    fornecedor_razao: str
    cnpj_fornecedor: str
    fornecedor2_razao: Optional[str] = None
    cnpj_fornecedor2: Optional[str] = None
    centro_custo: str
    tipo: str
    valor_total: float = 0.0
    tempo_contrato_meses: Optional[int] = None
    data_inicio_cobranca: Optional[date] = None
    dia_vencimento: int = 0
    identificadores: Optional[str] = None
    info_adicional: Optional[str] = None
    tem_rateio: bool = False
    empresas_rateio: Optional[str] = None
    caminho_arquivo: Optional[str] = None
    cancelado_em: Optional[str] = None
    ativo: bool = True
    
    class Config:
        populate_by_name = True

class FaturaDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    contrato_id: str
    mes_referencia: str
    valor: float
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    numero_circuito: Optional[str] = None
    status: str = "Pendente envio do boleto"
    desconto: float = 0.0
    acrescimo: float = 0.0
    valor_ajustado: float
    observacoes: Optional[str] = None
    caminho_arquivo: str
    caminho_nf: Optional[str] = None
    data_upload: date = Field(default_factory=datetime.now().date)
    ativo: bool = True
    
    class Config:
        populate_by_name = True

class CredencialDB(BaseModel):
    _id: Optional[str] = Field(None, alias="_id")
    nome_servico: str
    descricao: Optional[str] = None
    url_acesso: str
    usuario: str
    senha: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    responsavel: Optional[str] = None
    ativo: bool = True
    data_criacao: datetime = Field(default_factory=datetime.now)
    data_atualizacao: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True

app = FastAPI(title="Portal Gestão TI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Criar diretório de uploads se não existir
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

# --- FUNÇÕES AUXILIARES ---
async def get_db():
    return db

async def registrar_log(usuario: str, acao: str, alvo: str, alvo_id: str, detalhes: str):
    try:
        log = AuditLogDB(usuario=usuario, acao=acao, alvo=alvo, alvo_id=alvo_id, detalhes=detalhes[:500])
        await db["audit_logs"].insert_one(log.model_dump(by_alias=True, exclude_none=True))
    except Exception as e:
        print(f"Erro Log: {e}")

def safe_float(v):
    if not v: return 0.0
    try:
        # Remove R$, espaços e converte formato BR (1.200,50) para US (1200.50)
        limpo = str(v).replace('R$', '').replace(' ', '')
        if ',' in limpo and '.' in limpo: # Ex: 1.200,50
            limpo = limpo.replace('.', '').replace(',', '.')
        elif ',' in limpo: # Ex: 200,50
            limpo = limpo.replace(',', '.')
        return float(limpo)
    except: return 0.0

def safe_int(v):
    if not v: return 0
    try: return int(float(v))
    except: return 0

def safe_date(v):
    if not v: return None
    try: return datetime.strptime(v, "%Y-%m-%d").date()
    except: return None

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
    # Apenas admin e tercerizado podem ver credenciais
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

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), database = Depends(get_db)):
    user = await database["users"].find_one({"username": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")
    token = jwt.encode({"sub": user["username"], "role": user["role"]}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "username": user["username"], "foto_perfil": user.get("foto_perfil")}

# --- REGISTRO DE NOVO USUÁRIO (self-signup ou admin) ---
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    # Verifica se há um usuário fazendo request (admin)
    # Se não há usuário ou usuário não é admin, permite apenas o PRIMEIRO registro
    user_count = db.query(User).count()
    
    if user_count > 0 and current_user is None:
        raise HTTPException(status_code=403, detail="Registro não permitido. Consulte o administrador.")
    
    if current_user and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Apenas admins podem registrar novos usuários")
    
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Usuário deve ter no mínimo 3 caracteres")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    
    hashed = pwd_context.hash(password)
    novo = User(username=username, hashed_password=hashed, role="user", is_active=True)
    db.add(novo); db.commit(); db.refresh(novo)
    
    if current_user:
        registrar_log(db, current_user.username, "CREATE", "USER", novo.id, f"Novo usuário criado: {username}")
    
    token = jwt.encode({"sub": novo.username, "role": novo.role}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": novo.role, "username": novo.username, "status": "usuário criado"}

# --- PERFIL DO USUÁRIO ---
@app.get("/me")
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active, "foto_perfil": user.foto_perfil}

@app.put("/me/password")
async def change_password(current_password: str = Form(...), new_password: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not pwd_context.verify(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    
    return {"status": "senha alterada com sucesso"}

@app.post("/me/foto")
async def upload_foto_perfil(foto: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not foto.filename:
        raise HTTPException(status_code=400, detail="Arquivo não selecionado")
    
    # Validar tipo de arquivo
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if foto.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido. Use JPG, PNG, GIF ou WebP")
    
    # Criar nome único para a foto
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    extensao = foto.filename.split('.')[-1].lower()
    nome_arquivo = f"FOTO_{current_user.id}_{ts}.{extensao}"
    caminho_pasta = os.path.join(UPLOAD_DIR, "perfis")
    os.makedirs(caminho_pasta, exist_ok=True)
    
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    with open(caminho_completo, "wb") as f:
        shutil.copyfileobj(foto.file, f)
    
    # Atualizar usuário com novo caminho da foto
    user = db.query(User).filter(User.id == current_user.id).first()
    caminho_relativo = f"uploads/perfis/{nome_arquivo}"
    user.foto_perfil = caminho_relativo
    db.commit()
    
    registrar_log(db, current_user.username, "UPDATE", "USER", current_user.id, f"Atualizou foto de perfil")
    
    return {"status": "sucesso", "foto_url": caminho_relativo}

# --- ROTAS DE USUÁRIOS E LOGS ---
@app.get("/users/perfis")
def get_perfis(current_user: User = Depends(get_current_user)):
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
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    return db.query(User).all()

@app.post("/users/")
def create_user(username: str = Form(...), password: str = Form(...), role: str = Form("user"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    if db.query(User).filter(User.username == username).first(): raise HTTPException(status_code=400, detail="Usuário já existe")
    
    hashed = pwd_context.hash(password)
    novo = User(username=username, hashed_password=hashed, role=role)
    db.add(novo); db.commit()
    registrar_log(db, current_user.username, "CREATE", "USER", novo.id, f"Novo usuário: {username}")
    return {"status": "criado"}

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin': raise HTTPException(status_code=403, detail="Apenas admins podem deletar usuários")
    if user_id == current_user.id: raise HTTPException(status_code=400, detail="Não pode deletar sua própria conta")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    username_deletado = user.username
    db.delete(user)
    db.commit()
    registrar_log(db, current_user.username, "DELETE", "USER", user_id, f"Usuário deletado: {username_deletado}")
    return {"status": "usuário deletado"}

@app.put("/users/{user_id}/role")
def update_user_role(user_id: int, role: str = Form(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualiza o role/perfil de um usuário"""
    check_admin(current_user)
    if user_id == current_user.id: raise HTTPException(status_code=400, detail="Não pode alterar seu próprio perfil")
    
    # Validar role
    valid_roles = ['admin', 'normal', 'tercerizado']
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Deve ser um de: {', '.join(valid_roles)}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    role_antigo = user.role
    user.role = role
    db.commit()
    registrar_log(db, current_user.username, "UPDATE", "USER", user_id, f"Perfil alterado: {role_antigo} → {role}")
    return {"status": "perfil atualizado", "novo_role": role}

@app.get("/logs/")
def get_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_admin(current_user)
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()

@app.get("/historico/")
def get_historico(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o histórico de ações permitidas para o usuário"""
    verificar_permissao(current_user, PERMISSOES["historico"])
    
    query = db.query(AuditLog).order_by(AuditLog.id.desc())
    
    # Filtra histórico por perfil do usuário
    if current_user.role in ["normal", "tercerizado"]:
        # Normal e Tercerizado veem apenas Contratos, Faturas e Telefonia
        query = query.filter(AuditLog.alvo.in_(["CONTRATO", "FATURA", "TELEFONIA"]))
    # Admin vê tudo
    
    return query.limit(100).all()

# --- ROTAS CREDENCIAIS ---
@app.get("/dashboard/")
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna dados do dashboard para o usuário autenticado"""
    verificar_permissao(current_user, PERMISSOES["dashboard"])
    
    # Retorna estatísticas gerais
    total_contratos = db.query(Contrato).filter(Contrato.ativo == True).count()
    total_faturas = db.query(Fatura).count()
    total_numeros = db.query(NumeroTelefonico).filter(NumeroTelefonico.ativo == True).count()
    
    return {
        "usuario": current_user.username,
        "role": current_user.role,
        "total_contratos": total_contratos,
        "total_faturas": total_faturas,
        "total_numeros_telefonicos": total_numeros
    }

@app.get("/credenciais/")
def listar_credenciais(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_can_view_credentials(current_user)
    return db.query(Credencial).filter(Credencial.ativo == True).all()

@app.post("/credenciais/")
async def criar_credencial(
    nome_servico: str = Form(...), url_acesso: str = Form(...),
    usuario: str = Form(...), senha: str = Form(...),
    descricao: Optional[str] = Form(None), email: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None), responsavel: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    check_admin(current_user)
    
    nova = Credencial(
        nome_servico=nome_servico, url_acesso=url_acesso, usuario=usuario, senha=senha,
        descricao=descricao, email=email, telefone=telefone, responsavel=responsavel
    )
    db.add(nova); db.commit(); db.refresh(nova)
    registrar_log(db, current_user.username, "CREATE", "CREDENCIAL", nova.id, f"Nova credencial: {nome_servico}")
    return {"status": "criado", "id": nova.id}

@app.put("/credenciais/{id}")
async def editar_credencial(
    id: int,
    nome_servico: str = Form(...), url_acesso: str = Form(...),
    usuario: str = Form(...), senha: str = Form(...),
    descricao: Optional[str] = Form(None), email: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None), responsavel: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    check_admin(current_user)
    
    c = db.query(Credencial).filter(Credencial.id == id).first()
    if not c: raise HTTPException(status_code=404)
    
    c.nome_servico = nome_servico
    c.url_acesso = url_acesso
    c.usuario = usuario
    c.senha = senha
    c.descricao = descricao
    c.email = email
    c.telefone = telefone
    c.responsavel = responsavel
    c.data_atualizacao = datetime.now()
    
    db.commit()
    registrar_log(db, current_user.username, "UPDATE", "CREDENCIAL", id, f"Editou credencial: {nome_servico}")
    return {"status": "atualizado"}

@app.delete("/credenciais/{id}")
def excluir_credencial(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_admin(current_user)
    
    c = db.query(Credencial).filter(Credencial.id == id).first()
    if c:
        nome = c.nome_servico
        db.delete(c)
        db.commit()
        registrar_log(db, current_user.username, "DELETE", "CREDENCIAL", id, f"Excluiu credencial: {nome}")
    return {"status": "deleted"}

# --- ROTAS TELEFONIA ---
@app.get("/telefonia/")
def listar_numeros(operadora: Optional[str] = None, mes: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verificar_permissao(current_user, PERMISSOES["telefonia"])
    query = db.query(NumeroTelefonico)
    if operadora and operadora != 'Todos':
        query = query.filter(NumeroTelefonico.operadora == operadora)
    if mes:
        query = query.filter(NumeroTelefonico.mes_referencia == mes)
    return query.all()

@app.post("/telefonia/")
async def criar_numero(
    numero: str = Form(...), operadora: str = Form(...), valor: float = Form(...), 
    mes_referencia: str = Form(...), descricao: Optional[str] = Form(None),
    setor: Optional[str] = Form(None), filial: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    novo = NumeroTelefonico(
        numero=numero, operadora=operadora, valor=valor, mes_referencia=mes_referencia, 
        descricao=descricao, setor=setor, filial=filial
    )
    db.add(novo); db.commit()
    registrar_log(db, current_user.username, "CREATE", "TELEFONIA", novo.id, f"Adicionou {numero}")
    return {"status": "criado"}

@app.put("/telefonia/{id}")
async def editar_numero(
    id: int,
    numero: str = Form(...), operadora: str = Form(...), valor: float = Form(...), 
    mes_referencia: str = Form(...), descricao: Optional[str] = Form(None),
    setor: Optional[str] = Form(None), filial: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    n = db.query(NumeroTelefonico).filter(NumeroTelefonico.id == id).first()
    if not n: raise HTTPException(status_code=404)
    
    n.numero = numero
    n.operadora = operadora
    n.valor = valor
    n.mes_referencia = mes_referencia
    n.descricao = descricao
    n.setor = setor
    n.filial = filial
    
    db.commit()
    registrar_log(db, current_user.username, "UPDATE", "TELEFONIA", id, f"Editou {numero}")
    return {"status": "atualizado"}

@app.delete("/telefonia/{id}")
def excluir_numero(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    n = db.query(NumeroTelefonico).filter(NumeroTelefonico.id == id).first()
    if n: db.delete(n); db.commit()
    return {"status": "ok"}

# UPLOAD CSV TIM (Simples)
@app.post("/telefonia/upload/tim")
async def upload_tim_csv(
    mes_referencia: str = Form(...), arquivo: UploadFile = File(...),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    db.query(NumeroTelefonico).filter(NumeroTelefonico.operadora == 'Tim', NumeroTelefonico.mes_referencia == mes_referencia).delete()
    conteudo = await arquivo.read()
    decoded = conteudo.decode('utf-8', errors='replace').splitlines()
    reader = csv.reader(decoded)
    count = 0
    next(reader, None)
    for row in reader:
        if len(row) >= 3:
            try:
                num = row[0].strip()
                if not num.isdigit(): continue 
                db.add(NumeroTelefonico(
                    numero=num, operadora='Tim', descricao=row[1].strip(), 
                    valor=safe_float(row[2]), mes_referencia=mes_referencia,
                    setor="Indefinido", filial="Indefinido"
                ))
                count += 1
            except: continue
    db.commit()
    registrar_log(db, current_user.username, "UPLOAD", "TIM", 0, f"Importou {count} linhas")
    return {"status": "sucesso", "linhas_importadas": count}

# UPLOAD CSV INVENTÁRIO (Completo)
@app.post("/telefonia/upload/inventario")
async def upload_inventario_csv(
    mes_referencia: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Remove dados anteriores
    db.query(NumeroTelefonico).filter(NumeroTelefonico.mes_referencia == mes_referencia).delete()
    
    conteudo = await arquivo.read()
    decoded = conteudo.decode('utf-8', errors='replace').splitlines()
    reader = csv.reader(decoded, delimiter=';')
    
    count = 0
    header = next(reader, None) 
    
    for row in reader:
        # Baseado no seu arquivo numeros.csv (com ponto e vírgula):
        # 0: Nº Celular, 4: Filial, 5: Setor, 11: Operadora, 16: Valor Fatura
        if len(row) >= 17:
            try:
                raw_num = row[0]
                num = re.sub(r'\D', '', raw_num) # Limpa tudo que não é número
                
                if not num: continue

                filial = row[4].strip() if row[4].strip() else "Indefinido"
                setor = row[5].strip() if row[5].strip() else "Indefinido"
                operadora = row[11].strip() if row[11].strip() else "Desconhecida"
                valor = safe_float(row[16]) # Coluna 16 (Valor Fatura)

                db.add(NumeroTelefonico(
                    numero=num, operadora=operadora, descricao="Importado via Inventário",
                    valor=valor, mes_referencia=mes_referencia,
                    filial=filial, setor=setor
                ))
                count += 1
            except Exception as e: print(f"Erro linha: {e}")
            
    db.commit()
    registrar_log(db, current_user.username, "UPLOAD", "INVENTARIO", 0, f"Importou {count} linhas de inventário")
    return {"status": "sucesso", "linhas_importadas": count}

# --- ROTAS CONTRATOS ---
@app.get("/contratos/")
def listar_contratos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verificar_permissao(current_user, PERMISSOES["contratos"])
    return db.query(Contrato).filter(Contrato.ativo == True).order_by(Contrato.id.desc()).all()

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
    arquivo: UploadFile = File(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    path = None
    if arquivo:
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        name = f"CONTRATO_{ts}_{arquivo.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as b: shutil.copyfileobj(arquivo.file, b)
        path = f"uploads/{name}"

    if isinstance(tem_rateio, str): tem_rateio = tem_rateio.lower() in ['true', '1']

    novo = Contrato(
        nome_amigavel=nome_amigavel, filial=filial, fornecedor_razao=fornecedor_razao, cnpj_fornecedor=cnpj_fornecedor,
        fornecedor2_razao=fornecedor2_razao, cnpj_fornecedor2=cnpj_fornecedor2, centro_custo=centro_custo, tipo=tipo,
        valor_total=safe_float(valor_total), tempo_contrato_meses=safe_int(tempo_contrato_meses),
        data_inicio_cobranca=safe_date(data_inicio_cobranca), dia_vencimento=safe_int(dia_vencimento),
        identificadores=identificadores, info_adicional=info_adicional, tem_rateio=tem_rateio, empresas_rateio=empresas_rateio,
        caminho_arquivo=path
    )
    db.add(novo); db.commit(); db.refresh(novo)
    registrar_log(db, current_user.username, "CREATE", "CONTRATO", novo.id, f"Criou contrato {nome_amigavel}")
    return {"status": "criado"}

@app.put("/contratos/{id}")
async def editar_contrato(
    id: int, nome_amigavel: str = Form(...), filial: str = Form(...), 
    fornecedor_razao: str = Form(...), cnpj_fornecedor: str = Form(...),
    fornecedor2_razao: Optional[str] = Form(None), cnpj_fornecedor2: Optional[str] = Form(None),
    centro_custo: str = Form(...), tipo: str = Form(...),
    valor_total: Union[str, float] = Form(0), tempo_contrato_meses: Union[str, int] = Form(0),
    data_inicio_cobranca: Optional[str] = Form(None), dia_vencimento: Union[str, int] = Form(0),
    identificadores: Optional[str] = Form(None), info_adicional: Optional[str] = Form(None),
    tem_rateio: Union[str, bool] = Form(False), empresas_rateio: Optional[str] = Form(None),
    arquivo: UploadFile = File(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    c = db.query(Contrato).filter(Contrato.id == id).first()
    if not c: raise HTTPException(status_code=404)
    
    # Capturar alterações
    alteracoes = []
    novo_valor = safe_float(valor_total)
    novo_meses = safe_int(tempo_contrato_meses)
    
    if isinstance(tem_rateio, str): tem_rateio = tem_rateio.lower() in ['true', '1']
    
    if c.nome_amigavel != nome_amigavel: alteracoes.append(f"nome: {c.nome_amigavel}→{nome_amigavel}")
    if c.valor_total != novo_valor: alteracoes.append(f"valor: R${c.valor_total:.2f}→R${novo_valor:.2f}")
    if c.tempo_contrato_meses != novo_meses: alteracoes.append(f"meses: {c.tempo_contrato_meses}→{novo_meses}")
    if c.fornecedor_razao != fornecedor_razao: alteracoes.append(f"fornecedor: {c.fornecedor_razao}→{fornecedor_razao}")
    if c.filial != filial: alteracoes.append(f"filial alterada")
    if c.centro_custo != centro_custo: alteracoes.append(f"centro de custo alterado")
    if arquivo: alteracoes.append("arquivo atualizado")
    
    c.nome_amigavel = nome_amigavel; c.filial = filial; c.fornecedor_razao = fornecedor_razao; c.cnpj_fornecedor = cnpj_fornecedor
    c.fornecedor2_razao = fornecedor2_razao; c.cnpj_fornecedor2 = cnpj_fornecedor2; c.centro_custo = centro_custo; c.tipo = tipo
    c.valor_total = novo_valor; c.tempo_contrato_meses = novo_meses
    c.data_inicio_cobranca = safe_date(data_inicio_cobranca); c.dia_vencimento = safe_int(dia_vencimento)
    c.identificadores = identificadores; c.info_adicional = info_adicional; c.tem_rateio = tem_rateio; c.empresas_rateio = empresas_rateio
    
    if arquivo:
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        name = f"CONTRATO_{id}_{ts}_{arquivo.filename.replace(' ', '_')}"
        path = f"uploads/{name}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as b: shutil.copyfileobj(arquivo.file, b)
        c.caminho_arquivo = path
    
    db.commit()
    detalhes_log = f"{nome_amigavel}: {', '.join(alteracoes)}" if alteracoes else f"{nome_amigavel} editado (sem alterações)"
    registrar_log(db, current_user.username, "UPDATE", "CONTRATO", id, detalhes_log)
    return {"status": "atualizado"}

@app.delete("/contratos/{id}")
def excluir_contrato(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Contrato).filter(Contrato.id == id).first()
    if c:
        nome = c.nome_amigavel; db.delete(c); db.commit()
        registrar_log(db, current_user.username, "DELETE", "CONTRATO", id, f"Excluiu {nome}")
    return {"status": "deleted"}

@app.put("/contratos/{id}/inativar")
def inativar_contrato(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Contrato).filter(Contrato.id == id).first()
    if not c: raise HTTPException(status_code=404, detail="Contrato não encontrado")
    nome = c.nome_amigavel
    c.ativo = False
    db.commit()
    registrar_log(db, current_user.username, "INATIVAR", "CONTRATO", id, f"Inativou contrato: {nome}")
    return {"status": "inativado", "mensagem": f"Contrato '{nome}' inativado com sucesso"}

@app.put("/contratos/{id}/ativar")
def ativar_contrato(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Contrato).filter(Contrato.id == id).first()
    if not c: raise HTTPException(status_code=404, detail="Contrato não encontrado")
    nome = c.nome_amigavel
    c.ativo = True
    db.commit()
    registrar_log(db, current_user.username, "ATIVAR", "CONTRATO", id, f"Ativou contrato: {nome}")
    return {"status": "ativado", "mensagem": f"Contrato '{nome}' ativado com sucesso"}

# --- ROTAS FATURAS ---
@app.get("/faturas/")
def listar_faturas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): 
    verificar_permissao(current_user, PERMISSOES["faturas"])
    return db.query(Fatura).filter(Fatura.ativo == True).all()

@app.post("/faturas/")
async def lancar_fatura(
    contrato_id: Union[str, int] = Form(...), mes_referencia: str = Form(...), valor: Union[str, float] = Form(...),
    data_vencimento: Optional[str] = Form(None), numero_circuito: Optional[str] = Form(None),
    status: str = Form("Pendente envio do boleto"), desconto: Union[str, float] = Form(0.0), acrescimo: Union[str, float] = Form(0.0),
    observacoes: Optional[str] = Form(None), 
    arquivo: UploadFile = File(...), 
    arquivo_nf: UploadFile = File(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    path_boleto = f"uploads/BOLETO_{contrato_id}_{ts}_{arquivo.filename.replace(' ', '_')}"
    with open(os.path.join(UPLOAD_DIR, os.path.basename(path_boleto)), "wb") as b: shutil.copyfileobj(arquivo.file, b)
    
    path_nf = None
    if arquivo_nf:
        path_nf = f"uploads/NF_{contrato_id}_{ts}_{arquivo_nf.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path_nf)), "wb") as b: shutil.copyfileobj(arquivo_nf.file, b)

    v_val = safe_float(valor); v_desc = safe_float(desconto); v_acre = safe_float(acrescimo)
    
    nova = Fatura(
        contrato_id=safe_int(contrato_id), mes_referencia=mes_referencia, valor=v_val,
        valor_ajustado=v_val + v_acre - v_desc, desconto=v_desc, acrescimo=v_acre,
        data_vencimento=safe_date(data_vencimento), numero_circuito=numero_circuito,
        status=status, observacoes=observacoes, 
        caminho_arquivo=path_boleto, caminho_nf=path_nf
    )
    db.add(nova); db.commit(); db.refresh(nova)
    registrar_log(db, current_user.username, "CREATE", "FATURA", nova.id, f"Lançou fatura {mes_referencia}")
    return {"status": "sucesso"}

@app.put("/faturas/{id}")
async def editar_fatura(
    id: int, contrato_id: Union[str, int] = Form(...), mes_referencia: str = Form(...), valor: Union[str, float] = Form(...),
    data_vencimento: Optional[str] = Form(None), numero_circuito: Optional[str] = Form(None),
    desconto: Union[str, float] = Form(0.0), acrescimo: Union[str, float] = Form(0.0),
    observacoes: Optional[str] = Form(None), 
    arquivo: UploadFile = File(None), 
    arquivo_nf: UploadFile = File(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    f = db.query(Fatura).filter(Fatura.id == id).first()
    if not f: raise HTTPException(status_code=404)

    # Capturar valores antigos para log
    alteracoes = []
    v_val = safe_float(valor); v_desc = safe_float(desconto); v_acre = safe_float(acrescimo)
    novo_contrato_id = safe_int(contrato_id)
    
    if f.contrato_id != novo_contrato_id: alteracoes.append(f"contrato_id: {f.contrato_id}→{novo_contrato_id}")
    if f.mes_referencia != mes_referencia: alteracoes.append(f"mês: {f.mes_referencia}→{mes_referencia}")
    if f.valor != v_val: alteracoes.append(f"valor: R${f.valor:.2f}→R${v_val:.2f}")
    if f.desconto != v_desc: alteracoes.append(f"desconto: R${f.desconto:.2f}→R${v_desc:.2f}")
    if f.acrescimo != v_acre: alteracoes.append(f"acréscimo: R${f.acrescimo:.2f}→R${v_acre:.2f}")
    if data_vencimento and f.data_vencimento != safe_date(data_vencimento): alteracoes.append(f"vencimento: {f.data_vencimento}→{data_vencimento}")
    if numero_circuito and f.numero_circuito != numero_circuito: alteracoes.append(f"circuito: {f.numero_circuito}→{numero_circuito}")
    if observacoes and f.observacoes != observacoes: alteracoes.append("observações alteradas")
    if arquivo: alteracoes.append("boleto atualizado")
    if arquivo_nf: alteracoes.append("NF atualizada")

    f.contrato_id = novo_contrato_id; f.mes_referencia = mes_referencia; f.valor = v_val
    f.data_vencimento = safe_date(data_vencimento); f.numero_circuito = numero_circuito
    f.desconto = v_desc; f.acrescimo = v_acre; f.valor_ajustado = v_val + v_acre - v_desc
    f.observacoes = observacoes

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    if arquivo:
        path = f"uploads/BOLETO_{contrato_id}_{ts}_{arquivo.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path)), "wb") as b: shutil.copyfileobj(arquivo.file, b)
        f.caminho_arquivo = path
    if arquivo_nf:
        path = f"uploads/NF_{contrato_id}_{ts}_{arquivo_nf.filename.replace(' ', '_')}"
        with open(os.path.join(UPLOAD_DIR, os.path.basename(path)), "wb") as b: shutil.copyfileobj(arquivo_nf.file, b)
        f.caminho_nf = path

    db.commit()
    detalhes_log = f"Fatura #{id}: {', '.join(alteracoes)}" if alteracoes else f"Fatura #{id} editada (sem alterações)"
    registrar_log(db, current_user.username, "UPDATE", "FATURA", id, detalhes_log)
    return {"status": "atualizado"}

@app.put("/faturas/{id}/status")
async def atualizar_status(
    id: int, status: str = Form(...), data_pagamento: Optional[str] = Form(None), observacoes: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    f = db.query(Fatura).filter(Fatura.id == id).first()
    if f:
        status_anterior = f.status
        detalhes = f"Fatura #{id}: {status_anterior}→{status}"
        if data_pagamento: detalhes += f", pago em {data_pagamento}"
        if observacoes: detalhes += f", obs: {observacoes[:50]}"
        
        f.status = status
        if data_pagamento: f.data_pagamento = safe_date(data_pagamento)
        if observacoes: f.observacoes = observacoes
        db.commit()
        registrar_log(db, current_user.username, "UPDATE", "FATURA", id, detalhes)
    return {"status": "ok"}

@app.put("/faturas/{id}/inativar")
def inativar_fatura(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.query(Fatura).filter(Fatura.id == id).first()
    if not f: raise HTTPException(status_code=404, detail="Fatura não encontrada")
    f.ativo = False
    db.commit()
    registrar_log(db, current_user.username, "INATIVAR", "FATURA", id, f"Inativou fatura #{id}")
    return {"status": "inativado", "mensagem": f"Fatura #{id} inativada com sucesso"}

@app.put("/faturas/{id}/ativar")
def ativar_fatura(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.query(Fatura).filter(Fatura.id == id).first()
    if not f: raise HTTPException(status_code=404, detail="Fatura não encontrada")
    f.ativo = True
    db.commit()
    registrar_log(db, current_user.username, "ATIVAR", "FATURA", id, f"Ativou fatura #{id}")
    return {"status": "ativado", "mensagem": f"Fatura #{id} ativada com sucesso"}

@app.get("/dashboard/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    faturas = db.query(Fatura).all()
    contratos = db.query(Contrato).filter(Contrato.ativo == True).all()
    previsao = sum([c.valor_total / (c.tempo_contrato_meses if c.tempo_contrato_meses else 1) for c in contratos])
    return {
        "contratos_ativos": len(contratos),
        "faturas_pendentes": db.query(Fatura).filter(Fatura.status == "Pendente").count(),
        "total_faturas": len(faturas),
        "valor_contratos_mensal": previsao,
        "valor_pendente": sum([f.valor_ajustado for f in faturas if f.status == 'Pendente']),
        "valor_pago": sum([f.valor_ajustado for f in faturas if f.status == 'Pago'])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)