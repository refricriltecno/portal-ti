# deploy_render.ps1 - Script de deploy para Render (Windows)

Write-Host "🚀 Iniciando deploy para Render..." -ForegroundColor Green

# 1. Fazer backup
Write-Host "📦 Fazendo backup do arquivo original..." -ForegroundColor Yellow
if (Test-Path "backend/main.py") {
    Copy-Item "backend/main.py" "backend/main_postgres_backup.py" -Force -ErrorAction SilentlyContinue
}

# 2. Usar versão MongoDB
Write-Host "🔄 Ativando versão MongoDB..." -ForegroundColor Yellow
Copy-Item "backend/main_mongodb.py" "backend/main.py" -Force

# 3. Git
Write-Host "📤 Fazendo push para GitHub..." -ForegroundColor Yellow
git add backend/
git commit -m "Migração para MongoDB Atlas + Render" 2>$null
git push origin main

# 4. Instruções finais
Write-Host ""
Write-Host "✅ Código pronto para deploy!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos passos:" -ForegroundColor Cyan
Write-Host "1. Acesse https://render.com"
Write-Host "2. Conecte seu repositório GitHub"
Write-Host "3. Crie novo Web Service com:"
Write-Host "   - Build: pip install -r backend/requirements.txt"
Write-Host "   - Start: cd backend && python -m uvicorn main_mongodb:app --host 0.0.0.0 --port 8001"
Write-Host "4. Adicione variáveis de ambiente:"
Write-Host "   - DATABASE_URL=mongodb+srv://tecnologia_db_user:AdmRef212@refricril.lfg6bem.mongodb.net/?appName=Refricril"
Write-Host ""
Write-Host "📚 Consulte MIGRACAO_MONGODB_RENDER.md para mais detalhes" -ForegroundColor Cyan
