import discord
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from reynard_ai.bot_data.ai_bot import ReynardAIBotData

class ViewHistoryCommand(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, bot_data: ReynardAIBotData) -> None:
        self.discord_bot = discord_bot
        self.ai_bot_data =  bot_data
        
    @app_commands.command(
        name="chat_history", 
        description="View the chat history"
    )
    async def chat_history(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        embed = discord.Embed(title="Chat History",
            colour=0x00b0f4,
            timestamp=datetime.now()
        )
        embed.set_author(name="Info")

        last_msgs = self.ai_bot_data.short_term_memory._backing_history.as_list()[::-1]
        remaining_allowable_len = 3000
        MIN_MSGS_PER_EMBED = 5
        MAX_MSGS_PER_EMBED = 15
        for i, snapshot in enumerate(last_msgs):
            time = snapshot.sent.strftime("🕙 %d/%m %H:%M:%S ━━━━━━━━━━")
            pending = self.ai_bot_data.short_term_memory.is_pending(snapshot.message_id)
            name = f"{time} {'- PENDING' if pending else ''}"
            field_txt = snapshot.text[:1021]

            remaining_allowable_len -= len(snapshot.text)
            if i >= MIN_MSGS_PER_EMBED and remaining_allowable_len < 0:
                break
            if i >= MAX_MSGS_PER_EMBED:
                break

            embed.add_field(name=name, value=field_txt, inline=False)

        await interaction.followup.send(embed=embed)