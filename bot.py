import os
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# --- Configuração do Servidor Web para o UptimeRobot ---
app = Flask('')

@app.route('/')
def home():
    return "Bot está online e ativo!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Configurações dos IDs dos Canais ---
TOKEN = os.environ.get("TOKEN")

CANAL_ENTRADA_ID = 1561141242140557412    # Entrada
CANAL_APROVACAO_ID = 1561141268770455602  # Aprovação
CANAL_SAIU_ID = 1561141294800314428       # Saiu

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

class ConvidouSelect(discord.ui.Select):
    def __init__(self, membro: discord.Member):
        self.membro = membro
        # Filtra apenas Administradores do servidor que não sejam bots
        adms = [m for m in membro.guild.members if m.guild_permissions.administrator and not m.bot]
        opcoes = []
        for adm in adms[:25]:
            opcoes.append(
                discord.SelectOption(
                    label=adm.display_name,
                    value=str(adm.id),
                    description=f"Administrador: {adm.name}"
                )
            )
        if not opcoes:
            opcoes.append(
                discord.SelectOption(
                    label="Nenhum administrador encontrado",
                    value="0",
                    description="Contate a moderação"
                )
            )
        super().__init__(placeholder="Selecione qual Administrador te convidou...", min_values=1, max_values=1, options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        quem_convidou_id = int(self.values[0])
        await interaction.response.send_message("Obrigado! Sua resposta foi enviada para a moderação.", ephemeral=True)
        
        canal_aprovacao = interaction.guild.get_channel(CANAL_APROVACAO_ID)
        if canal_aprovacao:
            adm_selecionado = interaction.guild.get_member(quem_convidou_id)
            mencao_adm = adm_selecionado.mention if adm_selecionado else f"<@{quem_convidou_id}>"
            
            view = BotoesAprovacao(self.membro)
            # Marca o administrador selecionado para aprovar o novo membro
            await canal_aprovacao.send(
                content=f"{mencao_adm}, você deseja aprovar o/a {self.membro.mention} em seu servidor?",
                view=view
            )

class ViewEntrada(discord.ui.View):
    def __init__(self, membro: discord.Member):
        super().__init__(timeout=None)
        self.add_item(ConvidouSelect(membro))

class BotoesAprovacao(discord.ui.View):
    def __init__(self, membro: discord.Member):
        super().__init__(timeout=None)
        self.membro = membro

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.green)
    async def sim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"✅ {interaction.user.mention} **aprovou** a entrada de {self.membro.mention}.", view=None)

    @discord.ui.button(label="Não", style=discord.ButtonStyle.red)
    async def nao(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.membro.kick(reason="Não aprovado pelo sistema de verificação.")
            await interaction.response.edit_message(content=f"❌ {interaction.user.mention} **expulsou** {self.membro.name}.", view=None)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao expulsar: {e}", ephemeral=True)

    @discord.ui.button(label="Banir", style=discord.ButtonStyle.blurple)
    async def banir(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.membro.ban(reason="Banido pelo sistema de verificação.")
            await interaction.response.edit_message(content=f"🔨 {interaction.user.mention} **baniu** {self.membro.name}.", view=None)
        except Exception as e:
            await interaction.response.send_message(f"Erro ao banir: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot conectado com sucesso como {bot.user}!")

@bot.event
async def on_member_join(member: discord.Member):
    canal_entrada = member.guild.get_channel(CANAL_ENTRADA_ID)
    if canal_entrada:
        texto = f"Bem vindo a TG, um servidor privado somente para os mais proximos, selecione quem te convidou para o servidor, {member.mention}."
        view = ViewEntrada(member)
        await canal_entrada.send(content=texto, view=view)

@bot.event
async def on_member_remove(member: discord.Member):
    canal_saiu = member.guild.get_channel(CANAL_SAIU_ID)
    if canal_saiu:
        await canal_saiu.send(f"📤 O usuário **{member.name}** (`{member.mention}`) saiu do servidor.")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)