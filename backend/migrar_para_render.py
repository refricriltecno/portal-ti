#!/usr/bin/env python
"""
Script de Migração do Banco de Dados para Render
Faz dump do banco atual e restaura no Render
"""

import subprocess
import os
import sys
from datetime import datetime

# Configurações de conexão
BANCO_ORIGEM = {
    "host": "10.1.1.248",
    "port": "5432",
    "database": "portal_ti",
    "user": "portal_user",
    "password": "Adm@Ref212"
}

BANCO_RENDER = {
    "host": "dpg-d5tkluchg0os73812kqg-a.virginia-postgres.render.com",
    "port": "5432",
    "database": "portal_ti_db",
    "user": "portal_ti_db_user",
    "password": "EXpVxSf8CRCQ7X16fY2F4sdw93hMqOE9"
}

def fazer_dump():
    """Faz dump do banco atual para um arquivo SQL"""
    print("📊 Iniciando backup do banco de dados...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"backup_portal_ti_{timestamp}.sql"
    
    try:
        # Comando para fazer dump
        comando = [
            "pg_dump",
            f"--host={BANCO_ORIGEM['host']}",
            f"--port={BANCO_ORIGEM['port']}",
            f"--username={BANCO_ORIGEM['user']}",
            f"--dbname={BANCO_ORIGEM['database']}",
            "--format=plain",
            "--no-password",
            f"--file={nome_arquivo}"
        ]
        
        # Adiciona a senha via variável de ambiente (mais seguro)
        env = os.environ.copy()
        env['PGPASSWORD'] = BANCO_ORIGEM['password']
        
        print(f"  → Criando backup: {nome_arquivo}")
        resultado = subprocess.run(comando, env=env, capture_output=True, text=True)
        
        if resultado.returncode != 0:
            print(f"❌ Erro ao fazer dump: {resultado.stderr}")
            return None
        
        # Verifica se o arquivo foi criado
        if os.path.exists(nome_arquivo):
            tamanho_mb = os.path.getsize(nome_arquivo) / (1024 * 1024)
            print(f"✅ Backup criado com sucesso: {nome_arquivo} ({tamanho_mb:.2f} MB)")
            return nome_arquivo
        else:
            print(f"❌ Arquivo de backup não foi criado")
            return None
            
    except FileNotFoundError:
        print("❌ Erro: pg_dump não encontrado. Instale o PostgreSQL Client Tools.")
        print("   Windows: https://www.postgresql.org/download/windows/")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None

def restaurar_dump(arquivo_dump):
    """Restaura o dump no banco do Render"""
    print(f"\n📥 Restaurando backup no banco Render...")
    
    try:
        # Comando para restaurar
        comando = [
            "psql",
            f"--host={BANCO_RENDER['host']}",
            f"--port={BANCO_RENDER['port']}",
            f"--username={BANCO_RENDER['user']}",
            f"--dbname={BANCO_RENDER['database']}",
            "--no-password",
            f"--file={arquivo_dump}"
        ]
        
        # Adiciona a senha via variável de ambiente
        env = os.environ.copy()
        env['PGPASSWORD'] = BANCO_RENDER['password']
        env['PGSSLMODE'] = 'require'  # Render requer SSL
        
        print(f"  → Restaurando arquivo: {arquivo_dump}")
        print(f"  → Destino: {BANCO_RENDER['host']}")
        
        resultado = subprocess.run(comando, env=env, capture_output=True, text=True)
        
        if resultado.returncode != 0:
            print(f"❌ Erro ao restaurar: {resultado.stderr}")
            return False
        
        print(f"✅ Banco restaurado com sucesso no Render!")
        return True
        
    except FileNotFoundError:
        print("❌ Erro: psql não encontrado. Instale o PostgreSQL Client Tools.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def testar_conexao(config, nome):
    """Testa conexão com o banco"""
    print(f"\n🔗 Testando conexão com {nome}...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            sslmode='require' if 'render.com' in config['host'] else 'prefer'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Conta tabelas
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        num_tabelas = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✅ Conexão bem-sucedida com {nome}!")
        print(f"   → PostgreSQL: {version.split(',')[0]}")
        print(f"   → Tabelas: {num_tabelas}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO DE BANCO DE DADOS - Render")
    print("=" * 60)
    
    # Teste conexões
    print("\n📋 Verificando conexões...")
    if not testar_conexao(BANCO_ORIGEM, "banco atual (10.1.1.248)"):
        print("\n❌ Não foi possível conectar ao banco atual!")
        return False
    
    if not testar_conexao(BANCO_RENDER, "banco Render"):
        print("\n❌ Não foi possível conectar ao banco Render!")
        print("Verifique:")
        print("  - Credenciais de conexão")
        print("  - Firewall/Security Groups do Render")
        return False
    
    # Fazer backup
    print("\n" + "=" * 60)
    arquivo = fazer_dump()
    if not arquivo:
        print("\n❌ Falha ao criar backup!")
        return False
    
    # Restaurar
    print("\n" + "=" * 60)
    if not restaurar_dump(arquivo):
        print("\n❌ Falha ao restaurar backup!")
        return False
    
    # Teste final
    print("\n" + "=" * 60)
    if testar_conexao(BANCO_RENDER, "banco Render (pós-restauração)"):
        print("\n" + "=" * 60)
        print("✨ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("\n📝 Próximas etapas:")
        print("  1. Atualizar a variável DATABASE_URL em main.py:")
        print(f"     DATABASE_URL = \"postgresql://{BANCO_RENDER['user']}:{BANCO_RENDER['password']}@{BANCO_RENDER['host']}:5432/{BANCO_RENDER['database']}\"")
        print("\n  2. Ou defina a variável de ambiente DATABASE_URL")
        print(f"     export DATABASE_URL=\"postgresql://{BANCO_RENDER['user']}:{BANCO_RENDER['password']}@{BANCO_RENDER['host']}:5432/{BANCO_RENDER['database']}\"")
        print("\n  3. Reinicie o servidor Python")
        print(f"\n💾 Backup salvo em: {arquivo}")
        print("   (Guarde este arquivo como backup em caso de problemas)")
        return True
    else:
        print("\n❌ Erro ao verificar banco após restauração!")
        return False

if __name__ == "__main__":
    try:
        sucesso = main()
        sys.exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migração cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        sys.exit(1)
