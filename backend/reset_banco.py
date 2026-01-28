from sqlalchemy import create_engine, text

# --- CONFIGURAÇÃO ---
DATABASE_URL = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
engine = create_engine(DATABASE_URL)

def resetar():
    print("Conectando ao banco de dados...")
    with engine.connect() as conn:
        print("Apagando tabelas antigas...")
        conn.execute(text("DROP TABLE IF EXISTS faturas CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS contratos CASCADE;"))
        conn.commit()
        print("✅ Sucesso! Tabelas apagadas. O main.py vai recriar tudo novo.")

if __name__ == "__main__":
    resetar()