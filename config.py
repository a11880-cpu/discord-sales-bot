import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
VENDAS_CHANNEL_ID = int(os.getenv('VENDAS_CHANNEL_ID', 0))
CASHBACK_CHANNEL_ID = int(os.getenv('CASHBACK_CHANNEL_ID', 0))

# Configuração de Cashback por Cargo
CASHBACK_CONFIG = {
    'Aux': float(os.getenv('CASHBACK_AUX', 5)),
    'Junior': float(os.getenv('CASHBACK_JUNIOR', 7)),
    'Pleno': float(os.getenv('CASHBACK_PLENO', 10)),
    'Senior': float(os.getenv('CASHBACK_SENIOR', 15)),
    'Gerente': float(os.getenv('CASHBACK_GERENTE', 20))
}

# Ordem de hierarquia (quanto maior o índice, maior a posição)
HIERARCHY_ROLES = ['Aux', 'Junior', 'Pleno', 'Senior', 'Gerente']

def get_cashback_percentage(role_name):
    """Obtém a percentagem de cashback para um cargo"""
    return CASHBACK_CONFIG.get(role_name, 0)

def is_superior(user_roles):
    """Verifica se o usuário tem role de superior (Aux ou acima)"""
    for role in user_roles:
        if role.name in HIERARCHY_ROLES:
            return True
    return False

def get_highest_role(user_roles):
    """Obtém o cargo mais alto do usuário"""
    highest = None
    highest_index = -1
    
    for role in user_roles:
        if role.name in HIERARCHY_ROLES:
            index = HIERARCHY_ROLES.index(role.name)
            if index > highest_index:
                highest_index = index
                highest = role.name
    
    return highest