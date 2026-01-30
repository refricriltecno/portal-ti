#!/usr/bin/env python
"""Script para adicionar a coluna 'ativo' à tabela 'faturas'"""

import psycopg2
from psycopg2 import sql

# Configurações de conexão
conn_params = {
    "host": "10.1.1.248",
    "database": "portal_ti",
    "user": "portal_user",
    "password": "Adm@Ref212",
    "port": "5432"
}

try:
    # Conectar ao banco de dados
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    # Verificar se a coluna já existe
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'faturas' AND column_name = 'ativo'
    """)
    
    if cursor.fetchone():
        print("❌ Coluna 'ativo' já existe na tabela 'faturas'")
    else:
        # Adicionar a coluna
        cursor.execute("""
            ALTER TABLE faturas 
            ADD COLUMN ativo BOOLEAN DEFAULT TRUE
        """)
        conn.commit()
        print("✅ Coluna 'ativo' adicionada com sucesso à tabela 'faturas'")
    
    cursor.close()
    conn.close()
    
except psycopg2.Error as e:
    print(f"❌ Erro ao conectar ou executar: {e}")
except Exception as e:
    print(f"❌ Erro geral: {e}")
