#!/usr/bin/env python
"""
Script de Migração Simplificado para Render
Usa pg_dump e psql diretamente (mais confiável)
"""

import subprocess
import os
import sys
from datetime import datetime

# Configurações
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

def testar_conexao(config, nome):
    """Testa conexão com o banco usando psql"""
    print(f"🔗 Testando conexão com {nome}...")
    
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        cmd = [
            "psql",
            f"--host={config['host']}",
            f"--port={config['port']}",
            f"--username={config['user']}",
            f"--dbname={config['database']}",
            "--no-password",
            "-c", "SELECT version();"
        ]
        
        if "render.com" in config['host']:
            env['PGSSLMODE'] = 'require'
        
        resultado = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        
        if resultado.returncode != 0:
            print(f"❌ Erro: {resultado.stderr}")
            return False
        
        # Extrai versão
        for linha in resultado.stdout.split('\n'):
            if 'PostgreSQL' in linha:
                print(f"✅ {linha.strip()[:60]}...")
                return True
        
        print(f"✅ Conexão bem-sucedida!")
        return True
        
    except FileNotFoundError:
        print("❌ psql não encontrado. Instale PostgreSQL Client Tools.")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ao conectar (pode ser firewall)")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def migrar_com_pg_dump():
    """Migração direta usando pg_dump piped para psql"""
    print("\n📦 Iniciando migração com pg_dump...")
    
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = BANCO_ORIGEM['password']
        env['PGPASSWORD_RENDER'] = BANCO_RENDER['password']
        
        # Comando 1: pg_dump from origem
        cmd_dump = [
            "pg_dump",
            f"--host={BANCO_ORIGEM['host']}",
            f"--port={BANCO_ORIGEM['port']}",
            f"--username={BANCO_ORIGEM['user']}",
            f"--dbname={BANCO_ORIGEM['database']}",
            "--no-password",
            "--verbose",
            "--no-password"
        ]
        
        # Executar pg_dump
        print(f"  → Fazendo dump de {BANCO_ORIGEM['host']}...")
        dump_process = subprocess.Popen(cmd_dump, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Salvar em arquivo também (backup)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_portal_ti_{timestamp}.sql"
        
        with open(backup_file, 'wb') as f:
            for chunk in iter(lambda: dump_process.stdout.read(8192), b''):
                f.write(chunk)
        
        dump_process.wait()
        
        if dump_process.returncode != 0:
            stderr = dump_process.stderr.read().decode()
            print(f"❌ Erro ao fazer dump: {stderr}")
            return False
        
        tamanho_mb = os.path.getsize(backup_file) / (1024 * 1024)
        print(f"  → Backup criado: {backup_file} ({tamanho_mb:.2f} MB)")
        
        # Agora restaurar no Render
        print(f"  → Restaurando em {BANCO_RENDER['host']}...")
        
        env_render = os.environ.copy()
        env_render['PGPASSWORD'] = BANCO_RENDER['password']
        env_render['PGSSLMODE'] = 'require'
        
        cmd_restore = [
            "psql",
            f"--host={BANCO_RENDER['host']}",
            f"--port={BANCO_RENDER['port']}",
            f"--username={BANCO_RENDER['user']}",
            f"--dbname={BANCO_RENDER['database']}",
            "--no-password"
        ]
        
        with open(backup_file, 'rb') as f:
            restore_process = subprocess.Popen(
                cmd_restore,
                env=env_render,
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            restore_process.wait()
        
        if restore_process.returncode != 0:
            stderr = restore_process.stderr.read().decode()
            print(f"❌ Erro ao restaurar: {stderr}")
            return False
        
        print(f"✅ Dados restaurados com sucesso!")
        return True
        
    except FileNotFoundError:
        print("❌ pg_dump ou psql não encontrado.")
        print("   Instale PostgreSQL Client Tools: https://www.postgresql.org/download/windows/")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def contar_registros(config, nome):
    """Conta registros em cada tabela"""
    print(f"\n📊 Verificando dados em {nome}...")
    
    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        if "render.com" in config['host']:
            env['PGSSLMODE'] = 'require'
        
        cmd = [
            "psql",
            f"--host={config['host']}",
            f"--port={config['port']}",
            f"--username={config['user']}",
            f"--dbname={config['database']}",
            "--no-password",
            "-c", """
SELECT 
    schemaname,
    tablename,
    (SELECT count(*) FROM information_schema.tables WHERE table_name=tablename) as rows
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
            """
        ]
        
        resultado = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if resultado.returncode == 0:
            print(resultado.stdout)
        else:
            print(f"⚠️  Não foi possível contar registros")
        
    except Exception as e:
        print(f"⚠️  {e}")

def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO SIMPLIFICADA - Render")
    print("=" * 60)
    
    # Testar conexões
    print("\n🔌 Testando conectividade...")
    if not testar_conexao(BANCO_ORIGEM, "Banco Atual (10.1.1.248)"):
        print("\n❌ Não foi possível conectar ao banco atual!")
        return False
    
    if not testar_conexao(BANCO_RENDER, "Banco Render"):
        print("\n❌ Não foi possível conectar ao banco Render!")
        print("   Verifique credenciais ou firewall do Render")
        return False
    
    # Fazer migração
    print("\n" + "=" * 60)
    if not migrar_com_pg_dump():
        print("\n❌ Falha na migração!")
        return False
    
    # Verificar resultado
    print("\n" + "=" * 60)
    contar_registros(BANCO_ORIGEM, "Banco Origem")
    print()
    contar_registros(BANCO_RENDER, "Banco Render")
    
    # Sucesso
    print("\n" + "=" * 60)
    print("✨ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print("\n📝 Próximas etapas:")
    print("  1. Atualizar DATABASE_URL em main.py:")
    print(f"     DATABASE_URL = \"postgresql://{BANCO_RENDER['user']}:{BANCO_RENDER['password']}@{BANCO_RENDER['host']}:5432/{BANCO_RENDER['database']}\"")
    print("\n  2. Reiniciar o servidor: python main.py")
    
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
