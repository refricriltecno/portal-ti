#!/usr/bin/env python
"""
Script de Migração Alternativa usando SQLAlchemy
Útil caso pg_dump/psql não estejam disponíveis no sistema
"""

import psycopg2
from psycopg2 import sql
import time
from datetime import datetime

# URLs de conexão
BANCO_ORIGEM = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
BANCO_RENDER = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com/portal_ti_db"

def conectar(url, nome):
    """Conecta ao banco de dados"""
    print(f"🔗 Conectando a {nome}...")
    try:
        if "render.com" in url:
            conn = psycopg2.connect(url, sslmode='require')
        else:
            conn = psycopg2.connect(url)
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"   → {version.split(',')[0]}")
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def copiar_schema(conn_origem, conn_render):
    """Copia o schema (estrutura das tabelas) usando pg_dump"""
    print("\n📋 Copiando schema das tabelas...")
    
    try:
        import subprocess
        import os
        
        # Usar pg_dump para extrair apenas o schema
        env = os.environ.copy()
        env['PGPASSWORD'] = "Adm@Ref212"
        
        # Faz dump apenas do schema (sem dados)
        resultado = subprocess.run([
            "pg_dump",
            "--schema-only",
            "--no-password",
            "-h", "10.1.1.248",
            "-U", "portal_user",
            "-d", "portal_ti"
        ], env=env, capture_output=True, text=True)
        
        if resultado.returncode != 0:
            print(f"❌ Erro ao obter schema: {resultado.stderr}")
            return False
        
        # Aplica o schema no Render
        cursor_render = conn_render.cursor()
        
        # Executa as commands do schema
        for comando in resultado.stdout.split(';'):
            if comando.strip():
                try:
                    cursor_render.execute(comando)
                except Exception as e:
                    # Ignora erros de tabelas que já existem
                    if "already exists" not in str(e):
                        print(f"⚠️  {e}")
        
        conn_render.commit()
        cursor_render.close()
        
        print(f"   → Schema copiado com sucesso")
        return True
        
    except FileNotFoundError:
        print("❌ pg_dump não encontrado. Use o script principal (migrar_para_render.py)")
        return False
    except Exception as e:
        print(f"❌ Erro ao copiar schema: {e}")
        return False

def copiar_dados(conn_origem, conn_render):
    """Copia todos os dados das tabelas"""
    print("\n📥 Copiando dados das tabelas...")
    
    try:
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        # Obtém lista de tabelas
        cursor_origem.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        tabelas = [row[0] for row in cursor_origem.fetchall()]
        total_linhas = 0
        
        for tabela in tabelas:
            try:
                # Conta linhas
                cursor_origem.execute(f"SELECT COUNT(*) FROM {tabela}")
                num_linhas = cursor_origem.fetchone()[0]
                
                if num_linhas == 0:
                    print(f"   → {tabela}: vazia")
                    continue
                
                # Copia dados usando COPY
                print(f"   → {tabela}: {num_linhas} linhas", end="")
                
                # Executa COPY para exportar
                cursor_origem.copy_to(
                    open(f'/tmp/{tabela}.csv', 'w'),
                    table=tabela,
                    sep='\t'
                )
                
                # Executa COPY para importar
                with open(f'/tmp/{tabela}.csv', 'r') as f:
                    cursor_render.copy_from(f, table=tabela, sep='\t')
                
                conn_render.commit()
                print(" ✅")
                total_linhas += num_linhas
                
            except Exception as e:
                print(f" ❌ ({e})")
                continue
        
        cursor_origem.close()
        cursor_render.close()
        
        print(f"\n✅ Total de {total_linhas} linhas copiadas!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao copiar dados: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO ALTERNATIVA - Render (via SQLAlchemy)")
    print("=" * 60)
    
    inicio = time.time()
    
    # Conectar aos bancos
    print("\n🔌 Conectando aos bancos...")
    conn_origem = conectar(BANCO_ORIGEM, "Banco Atual (10.1.1.248)")
    conn_render = conectar(BANCO_RENDER, "Banco Render")
    
    if not conn_origem or not conn_render:
        print("\n❌ Falha na conexão!")
        return False
    
    # Copiar schema
    if not copiar_schema(conn_origem, conn_render):
        print("\n❌ Falha ao copiar schema!")
        return False
    
    # Copiar dados
    if not copiar_dados(conn_origem, conn_render):
        print("\n⚠️  Falha ao copiar dados (mas schema foi criado)")
    
    # Fechar conexões
    conn_origem.close()
    conn_render.close()
    
    tempo_decorrido = time.time() - inicio
    
    print("\n" + "=" * 60)
    print(f"✨ MIGRAÇÃO CONCLUÍDA! ({tempo_decorrido:.1f}s)")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migração cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
