import discord
from discord.ext import commands
from discord import app_commands
import config
from database import (
    init_database, registrar_venda, obter_venda, aprovar_venda, negar_venda,
    obter_saldo_cashback, solicitar_uso_cashback, aprovar_uso_cashback,
    negar_uso_cashback, obter_uso_cashback
)

# Inicializar bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Inicializar banco de dados
init_database()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} está online!')

# ==================== COMANDOS DE VENDAS ====================

@bot.tree.command(name="vendas", description="Registrar uma nova venda")
@app_commands.describe(
    valor="Valor da venda",
    descricao="Descrição da venda"
)
async def vendas(interaction: discord.Interaction, valor: float, descricao: str):
    """Registra uma venda e envia para o canal de aprovação"""
    
    try:
        # Validar valor
        if valor <= 0:
            await interaction.response.send_message("❌ O valor deve ser maior que 0!", ephemeral=True)
            return
        
        # Obter canal de vendas
        canal_vendas = bot.get_channel(config.VENDAS_CHANNEL_ID)
        if not canal_vendas:
            await interaction.response.send_message("❌ Canal de vendas não configurado!", ephemeral=True)
            return
        
        # Registrar venda (provisoriamente)
        venda_id = registrar_venda(
            interaction.user.id,
            interaction.user.name,
            valor,
            descricao,
            0
        )
        
        # Criar embed para o canal
        embed = discord.Embed(
            title=f"📊 Nova Venda Registrada - ID: {venda_id}",
            description=f"**Vendedor:** {interaction.user.mention}\n**Valor:** R$ {valor:.2f}\n**Descrição:** {descricao}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Venda ID: {venda_id}")
        
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
        
        # Responder ao usuário
        await interaction.response.send_message(
            f"✅ Venda registrada com sucesso!\n**ID da venda:** {venda_id}\n**Valor:** R$ {valor:.2f}",
            ephemeral=True
        )
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao registrar venda: {str(e)}", ephemeral=True)

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
            if venda and venda[5] == 'pendente':  # Status pendente
                # Calcular cashback
                user_obj = await reaction.message.guild.fetch_member(venda[1])
                role_name = config.get_highest_role(user_obj.roles)
                
                if role_name:
                    cashback_percentage = config.get_cashback_percentage(role_name)
                    cashback_value = venda[3] * (cashback_percentage / 100)
                    
                    # Aprovar venda e criar cashback
                    aprovar_venda(venda_id, cashback_value)
                    
                    # Atualizar embed
                    embed = mensagem.embeds[0]
                    embed.color = discord.Color.green()
                    embed.title = f"✅ Venda Aprovada - ID: {venda_id}"
                    embed.description += f"\n\n**Cashback Gerado:** R$ {cashback_value:.2f} ({cashback_percentage}%)"
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
            if venda and venda[5] == 'pendente':
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