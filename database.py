import sqlite3
import os
from datetime import datetime

DB_PATH = "sales_bot.db"

def init_database():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabela de vendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            valor REAL NOT NULL,
            descricao TEXT,
            status TEXT DEFAULT 'pendente',
            mensagem_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_aprovacao TIMESTAMP
        )
    ''')
    
    # Tabela de cashback dos usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cashback (
            user_id INTEGER PRIMARY KEY,
            saldo_total REAL DEFAULT 0,
            saldo_disponivel REAL DEFAULT 0,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de histórico de cashback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cashback_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            venda_id INTEGER,
            status TEXT DEFAULT 'pendente',
            mensagem_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_aprovacao TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def registrar_venda(user_id, user_name, valor, descricao, mensagem_id):
    """Registra uma nova venda"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO vendas (user_id, user_name, valor, descricao, mensagem_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, user_name, valor, descricao, mensagem_id))
    
    conn.commit()
    venda_id = cursor.lastrowid
    conn.close()
    
    return venda_id

def obter_venda(venda_id):
    """Obtém informações de uma venda"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM vendas WHERE id = ?', (venda_id,))
    venda = cursor.fetchone()
    conn.close()
    
    return venda

def aprovar_venda(venda_id, cashback_value):
    """Aprova uma venda e cria o cashback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Atualiza status da venda
    cursor.execute('''
        UPDATE vendas SET status = 'aprovada', data_aprovacao = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (venda_id,))
    
    # Obtém informações da venda
    cursor.execute('SELECT user_id FROM vendas WHERE id = ?', (venda_id,))
    user_id = cursor.fetchone()[0]
    
    # Registra o cashback
    cursor.execute('''
        INSERT INTO cashback_historico (user_id, tipo, valor, venda_id, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, 'ganho', cashback_value, venda_id, 'aprovada'))
    
    # Atualiza saldo de cashback
    cursor.execute('''
        INSERT INTO cashback (user_id, saldo_total, saldo_disponivel)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            saldo_total = saldo_total + ?,
            saldo_disponivel = saldo_disponivel + ?,
            ultima_atualizacao = CURRENT_TIMESTAMP
    ''', (user_id, cashback_value, cashback_value, cashback_value, cashback_value))
    
    conn.commit()
    conn.close()

def negar_venda(venda_id):
    """Nega uma venda"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE vendas SET status = 'negada', data_aprovacao = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (venda_id,))
    
    conn.commit()
    conn.close()

def obter_saldo_cashback(user_id):
    """Obtém o saldo de cashback disponível"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT saldo_disponivel, saldo_total FROM cashback WHERE user_id = ?', (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        return resultado[0], resultado[1]
    return 0, 0

def solicitar_uso_cashback(user_id, valor, mensagem_id):
    """Registra uma solicitação de uso de cashback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO cashback_historico (user_id, tipo, valor, status, mensagem_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, 'uso', valor, 'pendente', mensagem_id))
    
    conn.commit()
    cashback_id = cursor.lastrowid
    conn.close()
    
    return cashback_id

def aprovar_uso_cashback(cashback_id):
    """Aprova o uso de cashback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, valor FROM cashback_historico WHERE id = ?', (cashback_id,))
    resultado = cursor.fetchone()
    
    if resultado:
        user_id, valor = resultado
        
        # Atualiza status
        cursor.execute('''
            UPDATE cashback_historico SET status = 'aprovada', data_aprovacao = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (cashback_id,))
        
        # Deduz do saldo
        cursor.execute('''
            UPDATE cashback SET saldo_disponivel = saldo_disponivel - ?
            WHERE user_id = ?
        ''', (valor, user_id))
        
        conn.commit()
    
    conn.close()

def negar_uso_cashback(cashback_id):
    """Nega o uso de cashback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE cashback_historico SET status = 'negada', data_aprovacao = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (cashback_id,))
    
    conn.commit()
    conn.close()

def obter_uso_cashback(cashback_id):
    """Obtém informações de uso de cashback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM cashback_historico WHERE id = ?', (cashback_id,))
    resultado = cursor.fetchone()
    conn.close()
    
    return resultado