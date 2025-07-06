<<<<<<< HEAD
from ai_apis import providers
from bot_workflow.profile_loader import Profile
from bot_workflow.knowledge import KnowledgeIndex, LongTermMemoryIndex
from bot_workflow.bot_types import MessageSnapshotHistory, SynchronizedMessageHistory, AIBotData
=======
from abc import ABC
from ..ai_apis import providers
from ..bot_workflow.profile_loader import Profile
from ..bot_workflow.knowledge import KnowledgeIndex, LongTermMemoryIndex
from ..chat.message_history import MessageSnapshotHistory, SynchronizedMessageHistory

class AIBotData(ABC):
    def __init__(self, name: str, recent_memory: MessageSnapshotHistory | None = None):
        self.name = name
        self.memory = recent_memory
>>>>>>> cedb80f419dcaccec6d1fcdbcfa52d525983065c

class CustomBotData(AIBotData):
    def __init__(self,
                 *,
                 name: str,
                 profile: Profile,
                 provider_store: providers.ProviderDataStore,
                 knowledge: KnowledgeIndex,
                 long_term_memory: LongTermMemoryIndex | None,
                 discord_bot_id: int,
                 memory_length: int = 50
                ):
        super().__init__(name, MessageSnapshotHistory(memory_length=memory_length))
        self.profile = profile
        self.provider_store = provider_store
        self.discord_bot_id = discord_bot_id # TODO: tight coupling
        self.long_term_memory = long_term_memory
        self.full_history = SynchronizedMessageHistory()
        self.knowledge = knowledge 
