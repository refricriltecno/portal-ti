import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    print("🔐 Criando usuário admin...")
    
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
        
        # Dados do usuário admin
        username = "admin"
        password = "Adm@Ref212"  # Mude isso depois!
        
        # BCrypt tem limite de 72 bytes - truncar se necessário
        password_truncated = password[:72]
        
        # Verificar se já existe
        existing_user = await users_collection.find_one({"username": username})
        if existing_user:
            print(f"⚠️ Usuário '{username}' já existe!")
            client.close()
            return
        
        # Criar usuário
        user_data = {
            "username": username,
            "hashed_password": pwd_context.hash(password_truncated),
            "role": "admin",
            "is_active": True
        }
        
        result = await users_collection.insert_one(user_data)
        print(f"\n✅ Usuário criado com sucesso!")
        print(f"   ID: {result.inserted_id}")
        print(f"   Username: {username}")
        print(f"   Senha: {password}")
        print(f"   Role: admin")
        print(f"\n🔑 Credenciais de Login:")
        print(f"   Username: {username}")
        print(f"   Senha: {password}")
        print(f"\n⚠️  ALTERE A SENHA APÓS O PRIMEIRO LOGIN!")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin_user())
