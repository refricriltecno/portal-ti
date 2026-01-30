from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# --- CONFIGURAÇÃO ---
DATABASE_URL = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
engine = create_engine(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def migrar():
    print("🔄 Atualizando Banco de Dados...")
    
    comandos = [
        # Tabela Telefonia (NOVA ESTRUTURA)
        """CREATE TABLE IF NOT EXISTS numeros_telefonicos (
            id SERIAL PRIMARY KEY,
            numero VARCHAR,
            operadora VARCHAR, -- 'Tim' ou 'Vivo'
            descricao VARCHAR,
            valor FLOAT DEFAULT 0.0,
            mes_referencia VARCHAR,
            setor VARCHAR,  -- Novo
            filial VARCHAR, -- Novo
            ativo BOOLEAN DEFAULT TRUE,
            data_upload DATE DEFAULT CURRENT_DATE
        );""",
        
        # Garante colunas novas caso a tabela já exista
        "ALTER TABLE numeros_telefonicos ADD COLUMN IF NOT EXISTS setor VARCHAR;",
        "ALTER TABLE numeros_telefonicos ADD COLUMN IF NOT EXISTS filial VARCHAR;",

        # Tabelas de Sistema
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username VARCHAR UNIQUE NOT NULL, hashed_password VARCHAR NOT NULL, role VARCHAR DEFAULT 'user', is_active BOOLEAN DEFAULT TRUE
        );""",
        """CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY, usuario VARCHAR, acao VARCHAR, alvo VARCHAR, alvo_id INTEGER, detalhes TEXT, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        
        # Tabelas Financeiras
        """CREATE TABLE IF NOT EXISTS contratos (
            id SERIAL PRIMARY KEY, nome_amigavel VARCHAR, filial VARCHAR, fornecedor_razao VARCHAR, cnpj_fornecedor VARCHAR, 
            centro_custo VARCHAR, tipo VARCHAR, valor_total FLOAT, tempo_contrato_meses INTEGER, ativo BOOLEAN DEFAULT TRUE
        );""",
        """CREATE TABLE IF NOT EXISTS faturas (
            id SERIAL PRIMARY KEY, contrato_id INTEGER, mes_referencia VARCHAR, valor FLOAT, status VARCHAR, caminho_arquivo VARCHAR
        );""",

        # Atualizações de Colunas (Garante compatibilidade total)
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS caminho_nf VARCHAR;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS observacoes TEXT;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS data_pagamento DATE;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS data_vencimento DATE;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS numero_circuito VARCHAR;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'Pendente';",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS desconto FLOAT DEFAULT 0.0;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS acrescimo FLOAT DEFAULT 0.0;",
        "ALTER TABLE faturas ADD COLUMN IF NOT EXISTS valor_ajustado FLOAT DEFAULT 0.0;",
        
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS fornecedor2_razao VARCHAR;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS cnpj_fornecedor2 VARCHAR;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS valor_total FLOAT DEFAULT 0;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS data_inicio_cobranca DATE;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS dia_vencimento INTEGER DEFAULT 0;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS identificadores VARCHAR;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS info_adicional TEXT;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS tem_rateio BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS empresas_rateio VARCHAR;",
        "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS caminho_arquivo VARCHAR;"
    ]

    with engine.connect() as conn:
        for cmd in comandos:
            try:
                conn.execute(text(cmd))
                conn.commit()
            except Exception as e: print(f"Nota: {e}")
        
        # Admin Padrão
        try:
            if not conn.execute(text("SELECT * FROM users WHERE username = 'admin'")).first():
                hash_senha = pwd_context.hash("admin")
                conn.execute(text(f"INSERT INTO users (username, hashed_password, role) VALUES ('admin', '{hash_senha}', 'admin')"))
                conn.commit()
        except: pass

    print("✅ Banco Atualizado com Sucesso!")

if __name__ == "__main__":
    migrar()