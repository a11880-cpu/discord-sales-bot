import imagehash
from PIL import Image
import io
import aiohttp
import sqlite3

DB_PATH = "sales_bot.db"

def init_image_hash_table():
    """Inicializa a tabela de hashes de imagens"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            image_hash TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

async def download_image(image_url: str) -> Image.Image:
    """Baixa a imagem da URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(f"Erro ao baixar imagem: {e}")
    return None

async def calculate_image_hash(image_url: str) -> str:
    """Calcula o hash perceptual da imagem"""
    try:
        image = await download_image(image_url)
        if image:
            # Usar ahash (Average Hash) para detectar imagens similares
            return str(imagehash.average_hash(image))
    except Exception as e:
        print(f"Erro ao calcular hash: {e}")
    return None

def store_image_hash(venda_id: int, image_hash: str):
    """Armazena o hash da imagem no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO image_hashes (venda_id, image_hash)
        VALUES (?, ?)
    ''', (venda_id, image_hash))
    
    conn.commit()
    conn.close()

def get_all_image_hashes() -> list:
    """Obtém todos os hashes de imagens registrados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT venda_id, image_hash FROM image_hashes')
    hashes = cursor.fetchall()
    conn.close()
    
    return hashes

def is_image_duplicate(new_hash: str, similarity_threshold: int = 5) -> tuple:
    """
    Verifica se a imagem é um duplicado
    Retorna (is_duplicate, venda_id_original)
    
    similarity_threshold: máximo de diferenças de bits permitidas (0-64)
    Valores menores = verificação mais rigorosa
    5 = bastante rigoroso
    """
    try:
        new_hash_obj = imagehash.ImageHash(int(new_hash, 16))
        existing_hashes = get_all_image_hashes()
        
        for venda_id, existing_hash in existing_hashes:
            existing_hash_obj = imagehash.ImageHash(int(existing_hash, 16))
            
            # Calcular a diferença de Hamming entre os hashes
            hamming_distance = new_hash_obj - existing_hash_obj
            
            # Se a distância é menor que o threshold, as imagens são similares
            if hamming_distance <= similarity_threshold:
                return True, venda_id
        
        return False, None
    
    except Exception as e:
        print(f"Erro ao verificar duplicata: {e}")
        return False, None
