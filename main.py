import discord
import logging
import os
import hashlib
import glob

from dotenv import load_dotenv
from discord.ext import commands
from pydantic import BaseModel, Field
from commands.history import ViewHistoryCommand
from commands.sync_command_tree import SyncCommand
from commands.fal.image_gen_command import ImageGenCommand
from commands.fal.video_gen_command import VideoGenCommand
from commands.fal.image_edit_command import ImageEditCommand
from commands.fal.image_gen_hq_command import ImageGenHqCommand

import reynard_ai.util.logging_setup as logs
from reynard_ai.bot_data.bot_profile import Profile
from reynard_ai.chatbot.chatbot import ReynardChatBot
from reynard_ai.bot_data.ai_bot import ReynardAIBotData
from reynard_ai.ai_apis.providers import ProviderDataStore
from reynard_ai.util.environment_vars import get_environment_var
from reynard_ai.bot_data.knowledge import KnowledgeIndex, LongTermMemoryIndex, EmbeddingsClient

logs.setup()
load_dotenv()

MANIFEST_FILE = "knowledge_manifest.json"
KNOWLEDGE_DIR = "brain_content/knowledge"

class ManifestFileEntry(BaseModel):
    path: str
    sha256_hexdigest: str 

    @classmethod
    def from_file(cls, path: str) -> "ManifestFileEntry":
        with open(path, 'rb') as f:
            file_data = f.read()
            sha256_hexdigest = hashlib.sha256(file_data).hexdigest()
        return cls(path=path, sha256_hexdigest=sha256_hexdigest)

class KnowledgeManifest(BaseModel):
    files: list[ManifestFileEntry] = Field(default_factory=list)
    
    def get_hash(self, path: str) -> str | None:
        for entry in self.files:
            if entry.path == path:
                return entry.sha256_hexdigest
        return None

class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='p!', intents=intents)
        self.profile = Profile.from_file("profile.json")
        self.bot.event(self.on_ready)
        self.ai_bot_data: ReynardAIBotData | None = None

    def run(self):
        bot_token = get_environment_var('AI_BOT_TOKEN', required=True)
        self.bot.run(bot_token)

    async def setup_chatbot(self):
        embeddings_provider = self.profile.providers["EMBEDDINGS"]
        embedding_model_name = self.profile.get_request_params("EMBEDDINGS").model_name
        embedding_client = EmbeddingsClient(
            embeddings_provider, 
            embedding_model_name,
            3072 # TODO: make configurable
        )
    
        self.knowledge = await KnowledgeIndex.from_vectorizer(embedding_client)
        if self.profile.memory_settings.enable_long_term_memory:
            self.long_term_memory: LongTermMemoryIndex | None = await LongTermMemoryIndex.from_vectorizer(embedding_client)
        else:
            self.long_term_memory = None

        provider_list = [self.profile.providers[k] for k, v in self.profile.providers.items()]
        provider_store = ProviderDataStore(
            providers=provider_list
        ) # TODO: There should be required providers
        assert self.bot.user is not None
            
        self.ai_bot_data = ReynardAIBotData(
            profile=self.profile, 
            provider_store=provider_store,
            long_term_memory=self.long_term_memory,
            knowledge=self.knowledge,
            account_id=self.bot.user.id,
            memory_length=50            
        )
        await ReynardChatBot.create_discord_bot(self.bot, self.ai_bot_data)

    async def setup_commands(self):
        assert self.ai_bot_data is not None
        await self.bot.add_cog(SyncCommand(bot=self.bot))
        
        if self.profile.fal_image_gen_config.enabled:
            await self.bot.add_cog(ImageGenCommand(discord_bot=self.bot, bot_profile=self.profile))
            await self.bot.add_cog(ImageGenHqCommand(discord_bot=self.bot, bot_profile=self.profile))
            await self.bot.add_cog(ImageEditCommand(discord_bot=self.bot, bot_profile=self.profile))
            await self.bot.add_cog(VideoGenCommand(discord_bot=self.bot, bot_profile=self.profile))
            await self.bot.add_cog(ViewHistoryCommand(discord_bot=self.bot, bot_data=self.ai_bot_data))
        else:
            logging.info("Image generation using FAL.AI is disabled")

    async def index_knowledge(self):
        if os.path.exists(MANIFEST_FILE):
            with open(MANIFEST_FILE, 'r') as f:
                manifest = KnowledgeManifest.model_validate_json(f.read())
        else:
            manifest = KnowledgeManifest()

        current_file_paths = glob.glob(os.path.join(KNOWLEDGE_DIR, "**/*.txt"), recursive=True)
        new_entries: list[ManifestFileEntry] = []
        files_to_index: list[str] = []

        for filepath in current_file_paths:
            new_entry = ManifestFileEntry.from_file(path=filepath)
            new_entries.append(new_entry)
            stored_hash = manifest.get_hash(filepath)
            if stored_hash != new_entry.sha256_hexdigest:
                files_to_index.append(filepath)

        new_manifest = KnowledgeManifest(files=new_entries)
        if len(files_to_index) > 0:
            logging.info(f"Indexing {len(files_to_index)} changed files...")
            await self.knowledge.index_files(files_to_index)
            with open(MANIFEST_FILE, 'w') as f:
                f.write(new_manifest.model_dump_json(indent=4))
        elif new_manifest != manifest:
            with open(MANIFEST_FILE, 'w') as f:
                f.write(new_manifest.model_dump_json(indent=4))

    async def on_ready(self):
        logging.info("Creating chatbot...")
        await self.setup_chatbot()
        logging.info("Setting up commands...")
        await self.setup_commands()
        logging.info("Indexing knowledge...")
        await self.index_knowledge()
        logging.info(f'Logged in as {self.bot.user}')

bot = DiscordBot()
bot.run()