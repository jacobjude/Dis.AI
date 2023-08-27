import discord
from discord.ext import commands
import json

class DisAI(commands.Bot):
    def __init__(self, app_id):
        self.app_id = app_id
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        super().__init__(command_prefix='ai.', intents=intents, application_id=self.app_id)
        self.platforms = {}
        self.COOKIES = json.loads(open("./cookies.json", encoding="utf-8").read())
        self.left_guilds = []
