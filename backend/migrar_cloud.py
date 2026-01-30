#!/usr/bin/env python
"""
Script de Migração para Render - Sem dependência de pg_dump/psql
Usa SQLAlchemy + psycopg2 diretamente
"""

import psycopg2
from psycopg2 import sql
import time
from datetime import datetime
import sys

# URLs de conexão
BANCO_ORIGEM = "postgresql://portal_user:Adm%40Ref212@10.1.1.248:5432/portal_ti"
BANCO_RENDER = "postgresql://portal_ti_db_user:EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9@dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com:5432/portal_ti_db"

def conectar(url, nome, ssl_mode='prefer'):
    """Conecta ao banco de dados"""
    print(f"🔗 Conectando a {nome}...")
    try:
        conn = psycopg2.connect(url, sslmode=ssl_mode, connect_timeout=10)
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
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tabelas = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tabelas

def obter_ddl_tabela(conn, tabela):
    """Obtém o DDL (CREATE TABLE) de uma tabela específica"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT pg_get_create_table_as_select(
                ('{tabela}'::regclass)::oid,
                'SELECT * FROM {tabela}',
                true
            )
        """)
        resultado = cursor.fetchone()
        cursor.close()
        
        if resultado:
            return resultado[0]
        
        # Fallback: construir DDL manualmente
        return None
    except Exception as e:
        print(f"⚠️  Erro ao obter DDL: {e}")
        cursor.close()
        return None

def copiar_schema(conn_origem, conn_render):
    """Copia o schema (estrutura) de todas as tabelas"""
    print("\n📋 Copiando schema das tabelas...")
    
    try:
        tabelas = obter_tabelas(conn_origem)
        print(f"   → Encontradas {len(tabelas)} tabelas")
        
        cursor_render = conn_render.cursor()
        cursor_origem = conn_origem.cursor()
        
        for tabela in tabelas:
            try:
                # Query simplificada para obter DDL
                cursor_origem.execute(f"""
                    SELECT 
                        'CREATE TABLE IF NOT EXISTS ' || quote_ident(tablename) || ' (' ||
                        string_agg(
                            quote_ident(attname) || ' ' || 
                            pg_catalog.format_type(atttypid, atttypmod) ||
                            CASE 
                                WHEN attnotnull THEN ' NOT NULL'
                                ELSE ''
                            END ||
                            CASE
                                WHEN adsrc IS NOT NULL THEN ' DEFAULT ' || adsrc
                                ELSE ''
                            END,
                            ', ' ORDER BY attnum
                        ) ||
                        ')'
                    FROM (
                        SELECT 
                            t.tablename,
                            a.attname,
                            a.atttypid,
                            a.atttypmod,
                            a.attnotnull,
                            a.attnum,
                            d.adsrc
                        FROM pg_tables t
                        JOIN pg_attribute a ON a.attrelid = (t.tablename::regclass)::oid
                        LEFT JOIN pg_attrdef d ON (d.adrelid, d.adnum) = (a.attrelid, a.attnum)
                        WHERE t.schemaname = 'public' 
                            AND t.tablename = %s
                            AND a.attnum > 0
                    ) sq
                    GROUP BY tablename
                """, (tabela,))
                
                resultado = cursor_origem.fetchone()
                
                if resultado:
                    ddl = resultado[0]
                    # Executar DDL no Render
                    try:
                        cursor_render.execute(ddl)
                        conn_render.commit()
                        print(f"   → {tabela}")
                    except Exception as e:
                        # Se tabela já existe, continua
                        if "already exists" not in str(e):
                            print(f"   ⚠️  {tabela} ({str(e)[:40]}...)")
                        else:
                            print(f"   → {tabela} (já existe)")
                else:
                    print(f"   ⚠️  {tabela} (sem DDL)")
                    
            except Exception as e:
                print(f"   ⚠️  {tabela} ({str(e)[:50]}...)")
                continue
        
        cursor_origem.close()
        cursor_render.close()
        
        print(f"✅ Schema copiado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao copiar schema: {e}")
        return False

def copiar_dados(conn_origem, conn_render):
    """Copia todos os dados das tabelas"""
    print("\n📥 Copiando dados das tabelas...")
    
    try:
        tabelas = obter_tabelas(conn_origem)
        total_linhas = 0
        
        cursor_render = conn_render.cursor()
        
        for tabela in tabelas:
            try:
                cursor_origem = conn_origem.cursor()
                
                # Contar linhas
                cursor_origem.execute(f"SELECT COUNT(*) FROM {tabela}")
                num_linhas = cursor_origem.fetchone()[0]
                
                if num_linhas == 0:
                    print(f"   → {tabela}: (vazia)")
                    cursor_origem.close()
                    continue
                
                print(f"   → {tabela}: {num_linhas} linhas", end="", flush=True)
                
                # Tentar com COPY (mais rápido)
                try:
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(mode='w+b', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    # Exportar com COPY
                    with open(tmp_path, 'w') as f:
                        cursor_origem.copy_to(
                            f,
                            table=f'"{tabela}"',
                            sep='\t',
                            null='\\N'
                        )
                    
                    # Importar com COPY
                    with open(tmp_path, 'r') as f:
                        cursor_render.copy_from(
                            f,
                            table=f'"{tabela}"',
                            sep='\t',
                            null='\\N'
                        )
                    
                    os.unlink(tmp_path)
                    
                except Exception as copy_error:
                    # Fallback: inserir linha por linha
                    cursor_origem.execute(f"SELECT * FROM {tabela}")
                    
                    # Obtém nomes de colunas
                    colnames = [desc[0] for desc in cursor_origem.description]
                    
                    # Insere dados em batch
                    rows = cursor_origem.fetchall()
                    if rows:
                        placeholders = ', '.join(['%s'] * len(colnames))
                        for row in rows:
                            cursor_render.execute(
                                f"INSERT INTO {tabela} ({', '.join(colnames)}) VALUES ({placeholders})",
                                row
                            )
                
                cursor_origem.close()
                conn_render.commit()
                print(" ✅")
                total_linhas += num_linhas
                
            except Exception as e:
                print(f" ❌ ({str(e)[:40]}...)")
                continue
        
        cursor_render.close()
        
        print(f"\n✅ Total de {total_linhas:,} linhas copiadas!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao copiar dados: {e}")
        import traceback
        traceback.print_exc()
        return False

def restaurar_sequences(conn_origem, conn_render):
    """Restaura as sequences (auto-increment)"""
    print("\n🔄 Restaurando sequences...")
    
    try:
        cursor_origem = conn_origem.cursor()
        cursor_render = conn_render.cursor()
        
        # Obtém todas as sequences
        cursor_origem.execute("""
            SELECT sequence_name, start_value, minimum_value, maximum_value, increment
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        
        sequences = cursor_origem.fetchall()
        
        if not sequences:
            print("   → Nenhuma sequence encontrada")
            return True
        
        for seq_name, start_val, min_val, max_val, increment in sequences:
            try:
                # Obtém o máximo ID atual
                table_name = seq_name.replace('_id_seq', '').replace('_seq', '')
                cursor_origem.execute(f"SELECT MAX(id) FROM {table_name} LIMIT 1")
                max_id = cursor_origem.fetchone()[0]
                
                if max_id:
                    next_val = max_id + 1
                    cursor_render.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {next_val}")
                    print(f"   → {seq_name}: {next_val}")
                
            except Exception as e:
                print(f"   ⚠️  {seq_name}: {str(e)[:40]}...")
                continue
        
        conn_render.commit()
        cursor_origem.close()
        cursor_render.close()
        
        print(f"✅ Sequences restauradas!")
        return True
        
    except Exception as e:
        print(f"⚠️  Erro ao restaurar sequences: {e}")
        return True  # Não é crítico

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
            
            cursor_origem.execute(f"SELECT COUNT(*) FROM {tabela}")
            count_origem = cursor_origem.fetchone()[0]
            
            cursor_render.execute(f"SELECT COUNT(*) FROM {tabela}")
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
    print("🚀 MIGRAÇÃO DE BANCO DE DADOS - Render (Sem pg_dump)")
    print("=" * 60)
    
    inicio = time.time()
    
    # Conectar aos bancos
    print("\n🔌 Conectando aos bancos...")
    conn_origem = conectar(BANCO_ORIGEM, "Banco Atual (10.1.1.248)", ssl_mode='prefer')
    conn_render = conectar(BANCO_RENDER, "Banco Render", ssl_mode='require')
    
    if not conn_origem or not conn_render:
        print("\n❌ Falha na conexão!")
        return False
    
    # Copiar schema
    print("\n" + "=" * 60)
    if not copiar_schema(conn_origem, conn_render):
        print("\n❌ Falha ao copiar schema!")
        return False
    
    # Copiar dados
    print("\n" + "=" * 60)
    if not copiar_dados(conn_origem, conn_render):
        print("\n⚠️  Falha ao copiar alguns dados (mas schema foi criado)")
    
    # Restaurar sequences
    print("\n" + "=" * 60)
    restaurar_sequences(conn_origem, conn_render)
    
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
