import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")

async def check_users():
    print("🔍 Conectando ao MongoDB...")
    
    try:
        client = AsyncIOMotorClient(
            DATABASE_URL,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            tls=True,
            retryWrites=True,
            retryReads=True
        )
        
        await client.admin.command('ping')
        print("✅ Conectado ao MongoDB!")
        
        db = client["portal_ti"]
        
        # Listar todas as coleções
        collections = await db.list_collection_names()
        print(f"\n📋 Coleções disponíveis: {collections}")
        
        # Verificar usuários
        users_collection = db["users"]
        user_count = await users_collection.count_documents({})
        print(f"\n👥 Total de usuários: {user_count}")
        
        if user_count > 0:
            print("\n📝 Usuários cadastrados:")
            print("=" * 80)
            
            users = await users_collection.find({}).to_list(None)
            for user in users:
                print(f"ID: {user.get('_id')}")
                print(f"  Username: {user.get('username')}")
                print(f"  Role: {user.get('role')}")
                print(f"  Senha Hash: {user.get('hashed_password', 'NÃO DEFINIDA')[:50]}...")
                print()
        else:
            print("\n⚠️ Nenhum usuário cadastrado no banco!")
            print("Você precisa criar um usuário primeiro...")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(check_users())
