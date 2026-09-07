import discord
from discord.ext import commands
from discord import app_commands
import config
from database import (
    init_database, registrar_venda, obter_venda, aprovar_venda, negar_venda,
    obter_saldo_cashback, solicitar_uso_cashback, aprovar_uso_cashback,
    negar_uso_cashback, obter_uso_cashback
)
from image_analyzer import (
    init_image_hash_table, calculate_image_hash, store_image_hash, is_image_duplicate
)
import aiohttp
import asyncio

# Inicializar bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Inicializar banco de dados
init_database()
init_image_hash_table()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} está online!')

# ==================== MODAL DE VENDAS ====================

class VendaModal(discord.ui.Modal, title="Registrar Nova Venda"):
    nome_player = discord.ui.TextInput(
        label="Nome do Player",
        placeholder="Digite o nome do player...",
        required=True,
        max_length=100
    )
    
    id_player = discord.ui.TextInput(
        label="ID do Player",
        placeholder="Digite o ID do player...",
        required=True,
        max_length=100
    )
    
    valor = discord.ui.TextInput(
        label="Preço da Venda (R$)",
        placeholder="Ex: 150.00",
        required=True,
        max_length=20
    )
    
    produtos = discord.ui.TextInput(
        label="Produtos",
        placeholder="Descreva os produtos vendidos...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Processa o envio do modal"""
        try:
            # Validar valor
            try:
                valor_float = float(self.valor.value)
                if valor_float <= 0:
                    await interaction.response.send_message("❌ O valor deve ser maior que 0!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ O valor deve ser um número válido!", ephemeral=True)
                return
            
            # Enviar mensagem informando sobre o comprovativo
            await interaction.response.send_message(
                "✅ Formulário recebido! Agora envie uma foto do comprovativo neste canal para completar o registro.",
                ephemeral=True
            )
            
            # Aguardar o envio da foto
            def check(msg):
                return msg.author == interaction.user and len(msg.attachments) > 0 and msg.channel == interaction.channel
            
            try:
                msg_comprovativo = await bot.wait_for('message', check=check, timeout=300)  # 5 minutos
                
                # Obter a primeira anexação (foto)
                attachment = msg_comprovativo.attachments[0]
                comprovativo_url = attachment.url
                
                # Verificar se é uma imagem
                if not attachment.content_type or not attachment.content_type.startswith('image/'):
                    await interaction.followup.send(
                        "❌ O arquivo enviado não é uma imagem! Tente novamente com /vendas",
                        ephemeral=True
                    )
                    await msg_comprovativo.delete()
                    return
                
                # Enviar mensagem de análise
                await interaction.followup.send(
                    "🔍 Analisando imagem para detectar duplicatas...",
                    ephemeral=True
                )
                
                # Calcular hash da imagem
                image_hash = await calculate_image_hash(comprovativo_url)
                
                if not image_hash:
                    await interaction.followup.send(
                        "❌ Erro ao processar a imagem. Tente novamente com /vendas",
                        ephemeral=True
                    )
                    await msg_comprovativo.delete()
                    return
                
                # Verificar se é duplicada
                is_duplicate, venda_id_original = is_image_duplicate(image_hash)
                
                if is_duplicate:
                    await interaction.followup.send(
                        f"❌ **Imagem Duplicada!**\n\nEsta imagem é muito similar à venda ID **{venda_id_original}**. \nNão são permitidas imagens iguais ou muito similares.\n\nTente novamente com uma imagem diferente usando /vendas",
                        ephemeral=True
                    )
                    await msg_comprovativo.delete()
                    return
                
                # Registrar venda no banco de dados
                venda_id = registrar_venda(
                    interaction.user.id,
                    interaction.user.name,
                    self.nome_player.value,
                    self.id_player.value,
                    valor_float,
                    self.produtos.value,
                    comprovativo_url
                )
                
                # Armazenar hash da imagem
                store_image_hash(venda_id, image_hash)
                
                # Obter canal de vendas
                canal_vendas = bot.get_channel(config.VENDAS_CHANNEL_ID)
                if not canal_vendas:
                    await interaction.followup.send("❌ Canal de vendas não configurado!", ephemeral=True)
                    return
                
                # Criar embed com os dados da venda
                embed = discord.Embed(
                    title=f"📊 Nova Venda Registrada - ID: {venda_id}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="👤 Vendedor", value=f"{interaction.user.mention}", inline=False)
                embed.add_field(name="🎮 Nome do Player", value=self.nome_player.value, inline=True)
                embed.add_field(name="🔑 ID do Player", value=self.id_player.value, inline=True)
                embed.add_field(name="💰 Preço da Venda", value=f"R$ {valor_float:.2f}", inline=False)
                embed.add_field(name="📦 Produtos", value=self.produtos.value, inline=False)
                embed.add_field(name="📸 Comprovativo", value=f"[Ver comprovativo]({comprovativo_url})", inline=False)
                embed.add_field(name="✅ Status", value="Pendente de Análise", inline=False)
                embed.set_footer(text=f"Venda ID: {venda_id}")
                embed.set_image(url=comprovativo_url)
                
                # Enviar mensagem com reações
                mensagem = await canal_vendas.send(embed=embed)
                await mensagem.add_reaction('✅')
                await mensagem.add_reaction('❌')
                
                # Atualizar ID da mensagem no banco
                import sqlite3
                conn = sqlite3.connect('sales_bot.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE vendas SET mensagem_id = ? WHERE id = ?', (mensagem.id, venda_id))
                conn.commit()
                conn.close()
                
                # Confirmar ao usuário
                await interaction.followup.send(
                    f"✅ Venda registrada com sucesso!\n**ID da venda:** {venda_id}\n**Valor:** R$ {valor_float:.2f}\n\n📸 Imagem validada e armazenada!",
                    ephemeral=True
                )
                
                # Deletar mensagem do comprovativo
                await msg_comprovativo.delete()
                
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Tempo limite excedido! Tente novamente com /vendas", ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao processar formulário: {str(e)}", ephemeral=True)

# ==================== COMANDO DE VENDAS ====================

@bot.tree.command(name="vendas", description="Registrar uma nova venda com formulário")
async def vendas(interaction: discord.Interaction):
    """Abre um formulário para registrar uma nova venda"""
    await interaction.response.send_modal(VendaModal())

# ==================== COMANDOS DE CASHBACK ====================

@bot.tree.command(name="usocashback", description="Solicitar uso de cashback")
@app_commands.describe(valor="Valor de cashback a usar")
async def usar_cashback(interaction: discord.Interaction, valor: float):
    """Solicita uso de cashback para aprovação"""
    
    try:
        # Validar valor
        if valor <= 0:
            await interaction.response.send_message("❌ O valor deve ser maior que 0!", ephemeral=True)
            return
        
        # Verificar saldo disponível
        saldo_disponivel, saldo_total = obter_saldo_cashback(interaction.user.id)
        
        if saldo_disponivel < valor:
            await interaction.response.send_message(
                f"❌ Saldo insuficiente!\n**Disponível:** R$ {saldo_disponivel:.2f}\n**Solicitado:** R$ {valor:.2f}",
                ephemeral=True
            )
            return
        
        # Obter canal de cashback
        canal_cashback = bot.get_channel(config.CASHBACK_CHANNEL_ID)
        if not canal_cashback:
            await interaction.response.send_message("❌ Canal de cashback não configurado!", ephemeral=True)
            return
        
        # Registrar solicitação
        cashback_id = solicitar_uso_cashback(interaction.user.id, valor, 0)
        
        # Criar embed para o canal
        embed = discord.Embed(
            title=f"💰 Solicitação de Uso de Cashback - ID: {cashback_id}",
            description=f"**Usuário:** {interaction.user.mention}\n**Valor:** R$ {valor:.2f}\n**Saldo Disponível:** R$ {saldo_disponivel:.2f}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Cashback ID: {cashback_id}")
        
        # Enviar mensagem com reações
        mensagem = await canal_cashback.send(embed=embed)
        await mensagem.add_reaction('✅')
        await mensagem.add_reaction('❌')
        
        # Atualizar ID da mensagem no banco
        import sqlite3
        conn = sqlite3.connect('sales_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE cashback_historico SET mensagem_id = ? WHERE id = ?', (mensagem.id, cashback_id))
        conn.commit()
        conn.close()
        
        # Responder ao usuário
        await interaction.response.send_message(
            f"✅ Solicitação de cashback enviada para aprovação!\n**ID:** {cashback_id}\n**Valor:** R$ {valor:.2f}",
            ephemeral=True
        )
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao solicitar cashback: {str(e)}", ephemeral=True)

@bot.tree.command(name="saldocashback", description="Verificar saldo de cashback")
async def saldo_cashback(interaction: discord.Interaction):
    """Verifica o saldo de cashback do usuário"""
    
    try:
        saldo_disponivel, saldo_total = obter_saldo_cashback(interaction.user.id)
        
        embed = discord.Embed(
            title="💳 Saldo de Cashback",
            description=f"**Saldo Total:** R$ {saldo_total:.2f}\n**Disponível:** R$ {saldo_disponivel:.2f}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao verificar saldo: {str(e)}", ephemeral=True)

# ==================== SYSTEM DE REAÇÕES ====================

@bot.event
async def on_reaction_add(reaction, user):
    """Processa reações para aprovação de vendas e cashback"""
    
    # Ignorar reações do bot
    if user.bot:
        return
    
    # Verificar se o usuário é superior
    if not config.is_superior(user.roles):
        await reaction.remove(user)
        return
    
    # Processar reação
    if reaction.emoji == '✅':
        await processar_aprovacao(reaction, user)
    elif reaction.emoji == '❌':
        await processar_negacao(reaction, user)

async def processar_aprovacao(reaction, user):
    """Processa aprovação de vendas ou cashback"""
    
    try:
        mensagem = reaction.message
        
        # Verificar se é mensagem de venda
        if "Nova Venda Registrada" in mensagem.embeds[0].title:
            # Extrair ID da venda
            venda_id = int(mensagem.embeds[0].footer.text.split(": ")[1])
            
            venda = obter_venda(venda_id)
            if venda and venda[8] == 'pendente':  # Status pendente (índice 8)
                # Calcular cashback
                user_obj = await reaction.message.guild.fetch_member(venda[1])
                role_name = config.get_highest_role(user_obj.roles)
                
                if role_name:
                    cashback_percentage = config.get_cashback_percentage(role_name)
                    cashback_value = venda[5] * (cashback_percentage / 100)  # valor está no índice 5
                    
                    # Aprovar venda e criar cashback
                    aprovar_venda(venda_id, cashback_value)
                    
                    # Atualizar embed
                    embed = mensagem.embeds[0]
                    embed.color = discord.Color.green()
                    embed.title = f"✅ Venda Aprovada - ID: {venda_id}"
                    embed.add_field(name="✅ Status", value=f"Cashback Gerado: R$ {cashback_value:.2f} ({cashback_percentage}%)", inline=False)
                    embed.set_footer(text=f"Aprovada por: {user.name}")
                    
                    await mensagem.edit(embed=embed)
                    await mensagem.clear_reactions()
        
        # Verificar se é mensagem de cashback
        elif "Solicitação de Uso de Cashback" in mensagem.embeds[0].title:
            # Extrair ID do cashback
            cashback_id = int(mensagem.embeds[0].footer.text.split(": ")[1])
            
            cashback = obter_uso_cashback(cashback_id)
            if cashback and cashback[5] == 'pendente':  # Status pendente
                # Aprovar uso de cashback
                aprovar_uso_cashback(cashback_id)
                
                # Atualizar embed
                embed = mensagem.embeds[0]
                embed.color = discord.Color.green()
                embed.title = f"✅ Cashback Aprovado - ID: {cashback_id}"
                embed.set_footer(text=f"Aprovado por: {user.name}")
                
                await mensagem.edit(embed=embed)
                await mensagem.clear_reactions()
    
    except Exception as e:
        print(f"Erro ao processar aprovação: {e}")

async def processar_negacao(reaction, user):
    """Processa negação de vendas ou cashback"""
    
    try:
        mensagem = reaction.message
        
        # Verificar se é mensagem de venda
        if "Nova Venda Registrada" in mensagem.embeds[0].title:
            # Extrair ID da venda
            venda_id = int(mensagem.embeds[0].footer.text.split(": ")[1])
            
            venda = obter_venda(venda_id)
            if venda and venda[8] == 'pendente':  # Status pendente (índice 8)
                # Negar venda
                negar_venda(venda_id)
                
                # Atualizar embed
                embed = mensagem.embeds[0]
                embed.color = discord.Color.red()
                embed.title = f"❌ Venda Negada - ID: {venda_id}"
                embed.set_footer(text=f"Negada por: {user.name}")
                
                await mensagem.edit(embed=embed)
                await mensagem.clear_reactions()
        
        # Verificar se é mensagem de cashback
        elif "Solicitação de Uso de Cashback" in mensagem.embeds[0].title:
            # Extrair ID do cashback
            cashback_id = int(mensagem.embeds[0].footer.text.split(": ")[1])
            
            cashback = obter_uso_cashback(cashback_id)
            if cashback and cashback[5] == 'pendente':
                # Negar uso de cashback
                negar_uso_cashback(cashback_id)
                
                # Atualizar embed
                embed = mensagem.embeds[0]
                embed.color = discord.Color.red()
                embed.title = f"❌ Cashback Negado - ID: {cashback_id}"
                embed.set_footer(text=f"Negado por: {user.name}")
                
                await mensagem.edit(embed=embed)
                await mensagem.clear_reactions()
    
    except Exception as e:
        print(f"Erro ao processar negação: {e}")

# Executar bot
if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
