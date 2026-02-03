#!/bin/bash
# deploy_render.sh - Script para deploy no Render

echo "🚀 Iniciando deploy para Render..."

# 1. Fazer backup
echo "📦 Fazendo backup do arquivo original..."
cp backend/main.py backend/main_postgres_backup.py 2>/dev/null || true

# 2. Usar versão MongoDB
echo "🔄 Ativando versão MongoDB..."
cp backend/main_mongodb.py backend/main.py

# 3. Git
echo "📤 Fazendo push para GitHub..."
git add backend/
git commit -m "Migração para MongoDB Atlas + Render" || echo "⚠️ Nenhuma mudança para commit"
git push origin main

# 4. Instruções finais
echo ""
echo "✅ Código pronto para deploy!"
echo ""
echo "📋 Próximos passos:"
echo "1. Acesse https://render.com"
echo "2. Conecte seu repositório GitHub"
echo "3. Crie novo Web Service com:"
echo "   - Build: pip install -r backend/requirements.txt"
echo "   - Start: cd backend && python -m uvicorn main_mongodb:app --host 0.0.0.0 --port 8001"
echo "4. Adicione variáveis de ambiente:"
echo "   - DATABASE_URL=mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril"
echo ""
echo "📚 Consulte MIGRACAO_MONGODB_RENDER.md para mais detalhes"
