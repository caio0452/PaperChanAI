import discord
from datetime import datetime
from discord import Embed, app_commands
from discord.ext import commands
from core.bot_workflow.ai_responder import CustomBotData
from core.bot_workflow.profile_loader import Profile

class ViewHistoryCommand(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, ai_bot_data: CustomBotData, bot_profile: Profile) -> None:
        self.discord_bot = discord_bot
        self.bot_profile = bot_profile
        self.ai_bot_data = ai_bot_data
        
    @app_commands.command(
        name="chat_history", 
        description="View the chat history"
    )
    async def chat_history(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        await interaction.followup.send(embed=Embed(title="History"))
        embed = discord.Embed(title="Chat History",
            colour=0x00b0f4,
            timestamp=datetime.now()
        )
        embed.set_author(name="Info")

        last_5 = self.ai_bot_data.full_history.backing_history.as_list()[-5:]
        last_5.reverse()
        for snapshot in last_5:
            time = snapshot.sent.strftime("%d/%m/%Y %H:%M:%S")
            pending = self.ai_bot_data.full_history.is_pending(snapshot.message_id)
            name = f"{time} {'(PENDING)' if pending else ''}"
            value = snapshot.text[:1021]
            embed.add_field(name=name, value=value, inline=False)