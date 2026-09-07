# Discord Sales Bot 🤖💰

Bot Discord para gerenciar vendas e cashback com sistema de aprovação por hierarquia.

## Funcionalidades

✅ **`/vendas`** - Registrar novas vendas  
✅ **`/usocashback`** - Solicitar uso de cashback acumulado  
✅ **`/saldocashback`** - Verificar saldo de cashback disponível  
✅ **Sistema de Aprovação** - Superiores aprovam/negam com reações  
✅ **Cashback por Cargo** - Percentual diferente por role  
✅ **Banco de Dados SQLite** - Histórico completo de transações  

## Hierarquia de Usuários

Apenas usuários com as seguintes roles podem aprovar:

| Role | Cashback Padrão |
|------|------------------|
| Aux | 5% |
| Junior | 7% |
| Pleno | 10% |
| Senior | 15% |
| Gerente | 20% |

## Instalação

### 1. Clonar repositório

```bash
git clone https://github.com/a11880-cpu/discord-sales-bot.git
cd discord-sales-bot
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar arquivo `.env`

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Edite o `.env` com suas informações:

```env
DISCORD_TOKEN=seu_token_bot_aqui
GUILD_ID=seu_servidor_id
VENDAS_CHANNEL_ID=id_canal_vendas
CASHBACK_CHANNEL_ID=id_canal_cashback

# Opcional: Personalizar cashback por cargo
CASHBACK_AUX=5
CASHBACK_JUNIOR=7
CASHBACK_PLENO=10
CASHBACK_SENIOR=15
CASHBACK_GERENTE=20
```

### 4. Obter dados do Discord

**Token do Bot:**
1. Vá para https://discord.com/developers/applications
2. Crie uma nova aplicação
3. Vá em "Bot" e clique "Add Bot"
4. Copie o token em "TOKEN"

**IDs de Server e Canais:**
1. Ative Modo de Desenvolvedor no Discord
2. Clique direito no servidor → "Copiar ID do servidor"
3. Clique direito no canal → "Copiar ID do canal"

### 5. Criar canais (Opcional)

Crie dois canais no seu servidor:
- `#vendas-pendentes` - Para análise de vendas
- `#cashback-pendente` - Para análise de cashback

### 6. Executar o bot

```bash
python main.py
```

## Fluxo de Operação

### Registrar Venda

```
/vendas valor:500 descricao:"Venda de produto X"
```

**O que acontece:**
1. Venda é registrada com status "pendente"
2. Mensagem com embed é enviada para `#vendas-pendentes`
3. Superiores reagem com ✅ ou ❌
4. Se aprovada, cashback é calculado e adicionado ao saldo do vendedor

### Usar Cashback

```
/usocashback valor:50
```

**O que acontece:**
1. Sistema verifica saldo disponível
2. Se suficiente, solicitação é registrada
3. Mensagem é enviada para `#cashback-pendente`
4. Superiores reagem com ✅ ou ❌
5. Se aprovada, cashback é debitado

### Verificar Saldo

```
/saldocashback
```

Mostra saldo total e disponível de cashback.

## Estructura de Pastas

```
discord-sales-bot/
├── main.py              # Bot principal
├── database.py          # Funções de banco de dados
├── config.py            # Configurações
├── requirements.txt     # Dependências
├── .env.example         # Exemplo de configuração
├── .env                 # Configuração real (não commitar)
├── sales_bot.db         # Banco de dados SQLite
└── README.md            # Este arquivo
```

## Banco de Dados

### Tabelas

**vendas**
- id, user_id, user_name, valor, descricao, status, mensagem_id, data_criacao, data_aprovacao

**cashback**
- user_id, saldo_total, saldo_disponivel, ultima_atualizacao

**cashback_historico**
- id, user_id, tipo, valor, venda_id, status, mensagem_id, data_criacao, data_aprovacao

## Requisitos

- Python 3.8+
- discord.py 2.3.2+
- python-dotenv

## Permissões do Bot

Certifique-se de que o bot tem estas permissões no servidor:

- [x] Enviar Mensagens
- [x] Incorporar Links
- [x] Adicionar Reações
- [x] Ler Histórico de Mensagens
- [x] Gerenciar Mensagens

## Suporte

Para problemas ou dúvidas, abra uma issue no repositório!

## Licença

MIT License

---

**Desenvolvido com ❤️ para Discord**