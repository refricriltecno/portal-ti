#!/usr/bin/env python3
"""
test_mongodb_connection.py
Script para testar a conexão com MongoDB Atlas
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")

async def test_connection():
    """Testar conexão com MongoDB Atlas"""
    
    print("🔄 Testando conexão com MongoDB Atlas...")
    print(f"URL: {DATABASE_URL[:50]}...")
    print()
    
    try:
        # Criar cliente
        client = AsyncIOMotorClient(DATABASE_URL, serverSelectionTimeoutMS=5000)
        
        # Testar conexão
        print("⏳ Aguardando resposta do servidor...")
        await client.admin.command('ping')
        print("✅ Conexão bem-sucedida!")
        
        # Conectar ao banco
        db = client["portal_ti"]
        print(f"📊 Banco de dados: portal_ti")
        
        # Listar coleções
        print("\n📋 Coleções disponíveis:")
        collections = await db.list_collection_names()
        
        if collections:
            for coll in collections:
                count = await db[coll].count_documents({})
                print(f"   • {coll}: {count} documentos")
        else:
            print("   (Nenhuma coleção criada ainda)")
        
        # Criar índices
        print("\n⚙️  Criando índices...")
        try:
            await db["users"].create_index([("username", 1)], unique=True)
            print("   ✓ Índice em users.username criado")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # Testar inserção (opcional)
        print("\n🧪 Testando inserção de documento...")
        test_doc = {
            "teste": "conexão",
            "data": "2026-02-03",
            "status": "sucesso"
        }
        result = await db["teste"].insert_one(test_doc)
        print(f"   ✓ Documento inserido com ID: {result.inserted_id}")
        
        # Deletar teste
        await db["teste"].delete_one({"_id": result.inserted_id})
        print("   ✓ Documento de teste removido")
        
        print("\n" + "="*50)
        print("✅ TUDO FUNCIONANDO!")
        print("="*50)
        print("\n🎯 Próximos passos:")
        print("1. Copie main_mongodb.py para main.py")
        print("2. Rode: uvicorn main:app --reload")
        print("3. Acesse: http://localhost:8001/docs")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ ERRO DE CONEXÃO:")
        print(f"   {type(e).__name__}: {e}")
        print("\n🔍 Dicas:")
        print("1. Verificar string de conexão")
        print("2. Verificar lista branca de IPs no MongoDB Atlas")
        print("3. Verificar se a rede tem acesso à internet")
        print("4. Testar com: ping refricril.lfg6bem.mongodb.net")

if __name__ == "__main__":
    print("Portal TI - Teste de Conexão MongoDB\n")
    asyncio.run(test_connection())
