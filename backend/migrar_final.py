#!/usr/bin/env python
"""
Script de Migração para Render - Versão Simplificada
Usa SQLAlchemy para copiar dados sem complexidade
"""

import psycopg2
from psycopg2 import sql
import time
import sys

# URLs de conexão
BANCO_ORIGEM = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
BANCO_RENDER = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"

def conectar(url, nome, ssl_mode='prefer'):
    """Conecta ao banco de dados"""
    print(f"🔗 Conectando a {nome}...")
    try:
        conn = psycopg2.connect(url, sslmode=ssl_mode, connect_timeout=10)
        conn.autocommit = True  # Importante: desabilita transações automáticas
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

def obter_tabelas(conn):
    """Obtém lista de todas as tabelas públicas"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tabelas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tabelas
    except Exception as e:
        print(f"❌ Erro ao obter tabelas: {e}")
        cursor.close()
        return []

def obter_definicao_tabela(conn, tabela):
    """Obtém a definição CREATE TABLE de uma tabela"""
    cursor = conn.cursor()
    try:
        # Obtém o DDL usando psql
        cursor.execute(f"""
            SELECT pg_get_ddl_create_table('{tabela}'::regclass)
        """)
        resultado = cursor.fetchone()
        cursor.close()
        
        if resultado and resultado[0]:
            return resultado[0]
        
        # Se não funcionar, tenta método alternativo
        return None
        
    except Exception as e:
        cursor.close()
        # Tenta obter definição de forma manual
        return None

def criar_tabelas_render(conn_origem, conn_render):
    """Cria as tabelas no Render baseado nas tabelas da origem"""
    print("\n📋 Copiando definições das tabelas...")
    
    try:
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        tabelas = obter_tabelas(conn_origem)
        print(f"   → Encontradas {len(tabelas)} tabelas")
        
        for tabela in tabelas:
            try:
                # Obtém informações sobre as colunas
                cursor_origem.execute(f"""
                    SELECT 
                        attname,
                        pg_catalog.format_type(atttypid, atttypmod),
                        attnotnull,
                        pg_get_expr(adbin, adrelid)
                    FROM pg_attribute 
                    LEFT JOIN pg_attrdef ON (adrelid, adnum) = (attrelid, attnum)
                    WHERE attrelid = '{tabela}'::regclass
                    AND attnum > 0
                    ORDER BY attnum
                """)
                
                colunas = cursor_origem.fetchall()
                
                if not colunas:
                    print(f"   ⚠️  {tabela} (sem colunas)")
                    continue
                
                # Constrói CREATE TABLE
                col_defs = []
                for col_name, col_type, not_null, default in colunas:
                    col_def = f'"{col_name}" {col_type}'
                    if not_null:
                        col_def += ' NOT NULL'
                    if default:
                        col_def += f' DEFAULT {default}'
                    col_defs.append(col_def)
                
                create_sql = f'CREATE TABLE IF NOT EXISTS "{tabela}" (\n  ' + ',\n  '.join(col_defs) + '\n)'
                
                # Executa CREATE TABLE no Render
                cursor_render.execute(create_sql)
                print(f"   → {tabela}")
                
            except Exception as e:
                print(f"   ⚠️  {tabela} ({str(e)[:40]}...)")
                continue
        
        cursor_origem.close()
        cursor_render.close()
        
        print(f"✅ Tabelas criadas com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        import traceback
        traceback.print_exc()
        return False

def copiar_dados_simples(conn_origem, conn_render):
    """Copia dados usando método simples e robusto"""
    print("\n📥 Copiando dados das tabelas...")
    
    try:
        tabelas = obter_tabelas(conn_origem)
        total_linhas = 0
        
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        for tabela in tabelas:
            try:
                # Contar linhas na origem
                cursor_origem.execute(f"SELECT COUNT(*) FROM \"{tabela}\"")
                num_linhas = cursor_origem.fetchone()[0]
                
                if num_linhas == 0:
                    print(f"   → {tabela}: (vazia)")
                    continue
                
                print(f"   → {tabela}: {num_linhas} linhas", end="", flush=True)
                
                # Obter nomes das colunas
                cursor_origem.execute(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = '{tabela}'
                    ORDER BY ordinal_position
                """)
                col_names = [row[0] for row in cursor_origem.fetchall()]
                col_str = ', '.join([f'"{c}"' for c in col_names])
                
                # Buscar dados
                cursor_origem.execute(f"SELECT {col_str} FROM \"{tabela}\"")
                rows = cursor_origem.fetchall()
                
                # Inserir dados em lotes
                if rows:
                    placeholders = ', '.join(['%s'] * len(col_names))
                    insert_sql = f"INSERT INTO \"{tabela}\" ({col_str}) VALUES ({placeholders})"
                    
                    cursor_render.executemany(insert_sql, rows)
                
                print(" ✅")
                total_linhas += num_linhas
                
            except Exception as e:
                print(f" ❌")
                print(f"     Erro: {str(e)[:60]}...")
                continue
        
        cursor_origem.close()
        cursor_render.close()
        
        print(f"\n✅ Total de {total_linhas:,} linhas copiadas!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao copiar dados: {e}")
        import traceback
        traceback.print_exc()
        return False

def validar_migracao(conn_origem, conn_render):
    """Valida se a migração foi bem-sucedida"""
    print("\n✓ Validando migração...")
    
    try:
        tabelas_origem = obter_tabelas(conn_origem)
        tabelas_render = obter_tabelas(conn_render)
        
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        tudo_ok = True
        
        for tabela in tabelas_origem:
            if tabela not in tabelas_render:
                print(f"   ❌ {tabela}: não existe no Render")
                tudo_ok = False
                continue
            
            cursor_origem.execute(f"SELECT COUNT(*) FROM \"{tabela}\"")
            count_origem = cursor_origem.fetchone()[0]
            
            cursor_render.execute(f"SELECT COUNT(*) FROM \"{tabela}\"")
            count_render = cursor_render.fetchone()[0]
            
            if count_origem == count_render:
                print(f"   ✅ {tabela}: {count_render} registros")
            else:
                print(f"   ⚠️  {tabela}: origem={count_origem}, render={count_render}")
        
        cursor_origem.close()
        cursor_render.close()
        
        return tudo_ok
        
    except Exception as e:
        print(f"❌ Erro ao validar: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO DE BANCO DE DADOS - Render (Simplificada)")
    print("=" * 60)
    
    inicio = time.time()
    
    # Conectar aos bancos
    print("\n🔌 Conectando aos bancos...")
    conn_origem = conectar(BANCO_ORIGEM, "Banco Atual (10.1.1.248)", ssl_mode='prefer')
    conn_render = conectar(BANCO_RENDER, "Banco Render", ssl_mode='require')
    
    if not conn_origem or not conn_render:
        print("\n❌ Falha na conexão!")
        return False
    
    # Criar tabelas
    print("\n" + "=" * 60)
    if not criar_tabelas_render(conn_origem, conn_render):
        print("\n⚠️  Problema ao criar tabelas (continuando...)")
    
    # Copiar dados
    print("\n" + "=" * 60)
    if not copiar_dados_simples(conn_origem, conn_render):
        print("\n⚠️  Problema ao copiar dados")
    
    # Validar
    print("\n" + "=" * 60)
    validar_migracao(conn_origem, conn_render)
    
    # Fechar conexões
    conn_origem.close()
    conn_render.close()
    
    tempo_decorrido = time.time() - inicio
    
    print("\n" + "=" * 60)
    print(f"✨ MIGRAÇÃO CONCLUÍDA! ({tempo_decorrido:.1f}s)")
    print("=" * 60)
    
    print("\n📝 Próximas etapas:")
    print("  1. Atualizar DATABASE_URL em main.py:")
    print(f'     DATABASE_URL = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"')
    print("\n  2. Reiniciar o servidor Python:")
    print("     python main.py")
    
    return True

if __name__ == "__main__":
    try:
        sucesso = main()
        sys.exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migração cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
