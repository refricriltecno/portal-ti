import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")

async def delete_admin():
    print("🗑️  Deletando usuário admin...")
    
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
        users_collection = db["users"]
        
        result = await users_collection.delete_one({"username": "admin"})
        
        if result.deleted_count > 0:
            print(f"✅ Usuário admin deletado!")
        else:
            print(f"⚠️ Usuário admin não encontrado")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(delete_admin())
