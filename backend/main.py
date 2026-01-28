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
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, ForeignKey, Boolean, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- CONFIGURAÇÃO ---
DATABASE_URL = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
UPLOAD_DIR = "uploads"
SECRET_KEY = "segredo_super_seguro_refricril"
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SEGURANÇA ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# --- MODELOS ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String)
    acao = Column(String)
    alvo = Column(String)
    alvo_id = Column(Integer)
    detalhes = Column(Text)
    data_hora = Column(DateTime, default=datetime.now)

class NumeroTelefonico(Base):
    __tablename__ = "numeros_telefonicos"
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String)
    operadora = Column(String) 
    descricao = Column(String, nullable=True)
    valor = Column(Float, default=0.0)
    mes_referencia = Column(String)
    setor = Column(String, nullable=True)
    filial = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    data_upload = Column(Date, default=datetime.now().date)

class Contrato(Base):
    __tablename__ = "contratos"
    id = Column(Integer, primary_key=True, index=True)
    nome_amigavel = Column(String, index=True)
    filial = Column(String)
    fornecedor_razao = Column(String)
    cnpj_fornecedor = Column(String)
    fornecedor2_razao = Column(String, nullable=True)
    cnpj_fornecedor2 = Column(String, nullable=True)
    centro_custo = Column(String)
    tipo = Column(String)
    valor_total = Column(Float, default=0.0)
    tempo_contrato_meses = Column(Integer, nullable=True)
    data_inicio_cobranca = Column(Date, nullable=True)
    dia_vencimento = Column(Integer, default=0)
    identificadores = Column(String, nullable=True)
    info_adicional = Column(Text, nullable=True)
    tem_rateio = Column(Boolean, default=False)
    empresas_rateio = Column(String, nullable=True)
    caminho_arquivo = Column(String, nullable=True)
    cancelado_em = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    faturas = relationship("Fatura", back_populates="contrato", cascade="all, delete-orphan")

class Fatura(Base):
    __tablename__ = "faturas"
    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    mes_referencia = Column(String)
    valor = Column(Float)
    data_vencimento = Column(Date, nullable=True)
    data_pagamento = Column(Date, nullable=True)
    numero_circuito = Column(String, nullable=True)
    status = Column(String, default="Pendente")
    desconto = Column(Float, default=0.0)
    acrescimo = Column(Float, default=0.0)
    valor_ajustado = Column(Float)
    observacoes = Column(Text, nullable=True)
    caminho_arquivo = Column(String)
    caminho_nf = Column(String, nullable=True)
    data_upload = Column(Date, default=datetime.now().date)
    contrato = relationship("Contrato", back_populates="faturas")

class Credencial(Base):
    __tablename__ = "credenciais"
    id = Column(Integer, primary_key=True, index=True)
    nome_servico = Column(String, index=True)
    descricao = Column(String, nullable=True)
    url_acesso = Column(String)
    usuario = Column(String)
    senha = Column(String)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    responsavel = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.now)
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Portal Gestão TI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- FUNÇÕES AUXILIARES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def registrar_log(db: Session, usuario: str, acao: str, alvo: str, alvo_id: int, detalhes: str):
    try:
        log = AuditLog(usuario=usuario, acao=acao, alvo=alvo, alvo_id=alvo_id, detalhes=detalhes[:500])
        db.add(log)
        db.commit()
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
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401)
    return user

async def get_current_user_optional(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retorna o usuário atual se autenticado, ou None se não autenticado"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")
    token = jwt.encode({"sub": user.username, "role": user.role}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}

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
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active}

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

# --- ROTAS DE USUÁRIOS E LOGS ---
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

@app.get("/logs/")
def get_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()

# --- ROTAS CREDENCIAIS ---
@app.get("/credenciais/")
def listar_credenciais(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    return db.query(Credencial).filter(Credencial.ativo == True).all()

@app.post("/credenciais/")
async def criar_credencial(
    nome_servico: str = Form(...), url_acesso: str = Form(...),
    usuario: str = Form(...), senha: str = Form(...),
    descricao: Optional[str] = Form(None), email: Optional[str] = Form(None),
    telefone: Optional[str] = Form(None), responsavel: Optional[str] = Form(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    
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
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    
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
    if current_user.role != 'admin': raise HTTPException(status_code=403)
    
    c = db.query(Credencial).filter(Credencial.id == id).first()
    if c:
        nome = c.nome_servico
        db.delete(c)
        db.commit()
        registrar_log(db, current_user.username, "DELETE", "CREDENCIAL", id, f"Excluiu credencial: {nome}")
    return {"status": "deleted"}

# --- ROTAS TELEFONIA ---
@app.get("/telefonia/")
def listar_numeros(operadora: Optional[str] = None, mes: Optional[str] = None, db: Session = Depends(get_db)):
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
    return db.query(Contrato).order_by(Contrato.id.desc()).all()

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

# --- ROTAS FATURAS ---
@app.get("/faturas/")
def listar_faturas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)): 
    return db.query(Fatura).all()

@app.post("/faturas/")
async def lancar_fatura(
    contrato_id: Union[str, int] = Form(...), mes_referencia: str = Form(...), valor: Union[str, float] = Form(...),
    data_vencimento: Optional[str] = Form(None), numero_circuito: Optional[str] = Form(None),
    status: str = Form("Pendente"), desconto: Union[str, float] = Form(0.0), acrescimo: Union[str, float] = Form(0.0),
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