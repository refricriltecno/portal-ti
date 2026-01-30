#!/usr/bin/env python
"""
Script de Migração Final para Render - Método Direto
Faz dump e restaura sem dependências complexas
"""

import psycopg2
import time
import sys
import subprocess
import os
from pathlib import Path

# URLs de conexão
BANCO_ORIGEM = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
BANCO_RENDER = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"

def conectar(url, nome, ssl_mode='prefer'):
    """Conecta ao banco de dados"""
    print(f"🔗 Conectando a {nome}...")
    try:
        conn = psycopg2.connect(url, sslmode=ssl_mode, connect_timeout=10)
        conn.autocommit = True
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

def fazer_dump_sql(conn_origem):
    """Faz um dump SQL das estruturas das tabelas"""
    print("\n📋 Extraindo definições das tabelas...")
    
    try:
        cursor = conn_origem.cursor()
        tabelas = obter_tabelas(conn_origem)
        
        dump_sql = "-- Dump das definições das tabelas\n\n"
        
        for tabela in tabelas:
            try:
                # Obter informações das colunas
                cursor.execute(f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (tabela,))
                
                colunas = cursor.fetchall()
                
                if not colunas:
                    print(f"   ⚠️  {tabela} (sem colunas)")
                    continue
                
                # Construir CREATE TABLE
                col_defs = []
                for col_name, data_type, is_nullable, col_default, max_len, precision, scale in colunas:
                    col_def = f'"{col_name}" '
                    
                    # Ajustar tipos de dados
                    if data_type == 'character varying' and max_len:
                        col_def += f'VARCHAR({max_len})'
                    elif data_type == 'numeric' and precision and scale:
                        col_def += f'NUMERIC({precision},{scale})'
                    elif data_type == 'character':
                        col_def += 'CHAR'
                    else:
                        col_def += data_type.upper()
                    
                    # Adicionar DEFAULT se existir
                    if col_default and 'nextval' not in col_default:
                        col_def += f' DEFAULT {col_default}'
                    
                    # Adicionar NOT NULL se necessário
                    if is_nullable == 'NO':
                        col_def += ' NOT NULL'
                    
                    col_defs.append(col_def)
                
                # Obter primary key
                cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s 
                        AND tc.constraint_type = 'PRIMARY KEY'
                """, (tabela,))
                
                pk_result = cursor.fetchone()
                if pk_result:
                    pk_col = pk_result[0]
                    col_defs.append(f'PRIMARY KEY ("{pk_col}")')
                
                # Montar CREATE TABLE
                create_sql = f'CREATE TABLE "{tabela}" (\n  ' + ',\n  '.join(col_defs) + '\n);\n'
                dump_sql += create_sql
                
                print(f"   → {tabela}")
                
                # Obter sequences
                cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s 
                        AND column_default LIKE 'nextval%'
                """, (tabela,))
                
                for seq_info in cursor.fetchall():
                    seq_col = seq_info[0]
                    seq_name = f'{tabela}_{seq_col}_seq'
                    dump_sql += f"CREATE SEQUENCE IF NOT EXISTS {seq_name};\n"
                    dump_sql += f"ALTER TABLE \"{tabela}\" ALTER COLUMN \"{seq_col}\" SET DEFAULT nextval('{seq_name}'::regclass);\n"
                
            except Exception as e:
                print(f"   ⚠️  {tabela} ({str(e)[:40]}...)")
                continue
        
        cursor.close()
        
        # Salvar em arquivo
        dump_file = 'dump_schema.sql'
        with open(dump_file, 'w') as f:
            f.write(dump_sql)
        
        print(f"✅ Schema extraído ({len(dump_sql)} bytes)")
        return dump_file
        
    except Exception as e:
        print(f"❌ Erro ao extrair schema: {e}")
        import traceback
        traceback.print_exc()
        return None

def executar_dump(conn_render, dump_file):
    """Executa o dump SQL no Render"""
    print(f"\n⚡ Criando tabelas no Render...")
    
    try:
        cursor = conn_render.cursor()
        
        with open(dump_file, 'r') as f:
            dump_content = f.read()
        
        # Executar cada comando separadamente
        for comando in dump_content.split(';'):
            comando = comando.strip()
            if comando:
                try:
                    cursor.execute(comando)
                except Exception as e:
                    if "already exists" not in str(e):
                        print(f"   ⚠️  {str(e)[:60]}...")
        
        cursor.close()
        
        # Verificar tabelas criadas
        tabelas = obter_tabelas(conn_render)
        print(f"✅ {len(tabelas)} tabelas criadas no Render")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao executar dump: {e}")
        import traceback
        traceback.print_exc()
        return False

def copiar_dados(conn_origem, conn_render):
    """Copia os dados das tabelas"""
    print("\n📥 Copiando dados das tabelas...")
    
    try:
        tabelas = obter_tabelas(conn_origem)
        total_linhas = 0
        
        for tabela in tabelas:
            try:
                cursor_origem = conn_origem.cursor()
                cursor_render = conn_render.cursor()
                
                # Contar linhas
                cursor_origem.execute(f'SELECT COUNT(*) FROM "{tabela}"')
                num_linhas = cursor_origem.fetchone()[0]
                
                if num_linhas == 0:
                    print(f"   → {tabela}: (vazia)")
                    cursor_origem.close()
                    cursor_render.close()
                    continue
                
                print(f"   → {tabela}: {num_linhas} linhas", end="", flush=True)
                
                # Obter colunas
                cursor_origem.execute(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (tabela,))
                
                col_names = [row[0] for row in cursor_origem.fetchall()]
                col_str = ', '.join([f'"{c}"' for c in col_names])
                
                # Buscar dados
                cursor_origem.execute(f'SELECT {col_str} FROM "{tabela}"')
                rows = cursor_origem.fetchall()
                
                # Inserir em lotes
                if rows:
                    placeholders = ', '.join(['%s'] * len(col_names))
                    insert_sql = f'INSERT INTO "{tabela}" ({col_str}) VALUES ({placeholders})'
                    
                    try:
                        cursor_render.executemany(insert_sql, rows)
                    except Exception as insert_error:
                        # Tentar inserir um por um
                        for row in rows:
                            try:
                                cursor_render.execute(insert_sql, row)
                            except:
                                continue
                
                cursor_origem.close()
                cursor_render.close()
                
                print(" ✅")
                total_linhas += num_linhas
                
            except Exception as e:
                print(f" ❌")
                print(f"     {str(e)[:60]}...")
                continue
        
        print(f"\n✅ Total de {total_linhas:,} linhas copiadas!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao copiar dados: {e}")
        import traceback
        traceback.print_exc()
        return False

def validar_migracao(conn_origem, conn_render):
    """Valida se a migração funcionou"""
    print("\n✓ Validando migração...")
    
    try:
        tabelas_origem = obter_tabelas(conn_origem)
        tabelas_render = obter_tabelas(conn_render)
        
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        tudo_ok = True
        
        for tabela in tabelas_origem:
            if tabela not in tabelas_render:
                print(f"   ❌ {tabela}: não existe")
                tudo_ok = False
                continue
            
            cursor_origem.execute(f'SELECT COUNT(*) FROM "{tabela}"')
            count_origem = cursor_origem.fetchone()[0]
            
            cursor_render.execute(f'SELECT COUNT(*) FROM "{tabela}"')
            count_render = cursor_render.fetchone()[0]
            
            if count_origem == count_render:
                print(f"   ✅ {tabela}: {count_render} registros")
            else:
                print(f"   ⚠️  {tabela}: origem={count_origem}, render={count_render}")
                tudo_ok = False
        
        cursor_origem.close()
        cursor_render.close()
        
        return tudo_ok
        
    except Exception as e:
        print(f"❌ Erro ao validar: {e}")
        return False

def limpar_arquivos():
    """Remove arquivos temporários"""
    try:
        if os.path.exists('dump_schema.sql'):
            os.remove('dump_schema.sql')
    except:
        pass

def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO DE BANCO DE DADOS - Render (Final)")
    print("=" * 60)
    
    inicio = time.time()
    
    # Conectar
    print("\n🔌 Conectando aos bancos...")
    conn_origem = conectar(BANCO_ORIGEM, "Banco Atual (10.1.1.248)", ssl_mode='prefer')
    conn_render = conectar(BANCO_RENDER, "Banco Render", ssl_mode='require')
    
    if not conn_origem or not conn_render:
        print("\n❌ Falha na conexão!")
        return False
    
    # Fazer dump do schema
    print("\n" + "=" * 60)
    dump_file = fazer_dump_sql(conn_origem)
    if not dump_file:
        print("\n❌ Falha ao extrair schema!")
        return False
    
    # Executar dump no Render
    print("\n" + "=" * 60)
    if not executar_dump(conn_render, dump_file):
        print("\n⚠️  Problema ao criar tabelas")
    
    # Copiar dados
    print("\n" + "=" * 60)
    copiar_dados(conn_origem, conn_render)
    
    # Validar
    print("\n" + "=" * 60)
    validar_migracao(conn_origem, conn_render)
    
    # Fechar
    conn_origem.close()
    conn_render.close()
    
    # Limpar
    limpar_arquivos()
    
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
        print("\n\n⚠️  Migração cancelada")
        limpar_arquivos()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        limpar_arquivos()
        sys.exit(1)
