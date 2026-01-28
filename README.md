# Portal TI - Sistema de Gestão de Contratos e Telefonia

O **Portal TI** é uma solução completa desenvolvida para departamentos de Tecnologia da Informação gerenciarem custos, ativos e contratos. O sistema oferece controle financeiro detalhado sobre contratos de fornecedores, gestão de linhas telefônicas corporativas e centralização de credenciais de acesso.

![Status do Projeto](https://img.shields.io/badge/status-em_desenvolvimento-orange)
![Python](https://img.shields.io/badge/backend-FastAPI-009688)
![React](https://img.shields.io/badge/frontend-React_Vite-61DAFB)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-336791)

## 🚀 Funcionalidades Principais

### 📊 Dashboard
- Visão geral de custos previstos vs. realizados.
- Indicadores de faturas pendentes e pagas.
- Cálculo automático de divergências financeiras.

### 📄 Gestão de Contratos
- Cadastro completo de contratos (Serviços, Produtos ou Misto).
- Controle de vigência, dia de vencimento e centros de custo.
- Upload e armazenamento de contratos digitalizados (PDF).
- Suporte a rateio de custos entre filiais.

### 💰 Controle de Faturas
- Lançamento mensal de faturas vinculadas aos contratos.
- Anexo de boletos e notas fiscais.
- Workflow de status (Pendente, Enviado, Pago).
- Auditoria de valores (acréscimos, descontos e valor ajustado).

### 📱 Gestão de Telefonia
- Inventário de linhas telefônicas móveis.
- Importação de faturas via CSV (Layout TIM e Inventário Geral).
- Rateio de custos de telefonia por filial e centro de custo.

### 🔐 Segurança e Admin
- Gestão de Usuários e Permissões (Admin/User).
- Logs de Auditoria (Quem fez o quê e quando).
- Cofre de Senhas/Credenciais para serviços terceirizados.

## 🛠️ Tecnologias Utilizadas

**Backend:**
- **Linguagem:** Python 3.x
- **Framework:** FastAPI
- **ORM:** SQLAlchemy
- **Banco de Dados:** PostgreSQL
- **Autenticação:** JWT (JSON Web Tokens) com OAuth2

**Frontend:**
- **Framework:** React.js (via Vite)
- **Estilização:** Tailwind CSS + Lucide Icons
- **HTTP Client:** Axios

## ⚙️ Instalação e Configuração

### Pré-requisitos
- Python 3.9+
- Node.js 18+
- PostgreSQL

### 1. Configurando o Backend

```bash
# Clone o repositório
git clone [https://github.com/seu-usuario/portal-ti.git](https://github.com/seu-usuario/portal-ti.git)
cd portal-ti/backend

# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente (Crie um arquivo .env)
# DATABASE_URL=postgresql://user:senha@localhost:5432/portal_ti
# SECRET_KEY=sua_chave_secreta

# Execute o servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8001
2. Configurando o Frontend
Bash
cd ../frontend

# Instale as dependências
npm install

# Execute o projeto
npm run dev
🔒 Segurança
O sistema implementa:

Hashing de senhas com bcrypt.

Rotas protegidas via Token Bearer (JWT).

Logs de auditoria imutáveis para rastreabilidade de ações.

🤝 Contribuição
Faça um Fork do projeto

Crie uma Branch para sua Feature (git checkout -b feature/NovaFeature)

Faça o Commit (git commit -m 'Add some NovaFeature')

Faça o Push (git push origin feature/NovaFeature)

Abra um Pull Request

Desenvolvido por Luis Gustavo Zanatta
