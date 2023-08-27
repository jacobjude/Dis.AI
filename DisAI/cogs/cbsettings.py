import asyncio
import json
import logging

import discord
from discord import Colour
from discord.ext import commands
from EdgeGPT.EdgeGPT import Chatbot
from core.ChatBot import chatbot_clone
from config import TIMEOUT_TIME, MEMORY_LENGTH
from extensions.constants import Analytics
from extensions.embeds import get_credits_needed_embed
import extensions.helpers as helpers
from extensions.uiactions import CreateCBView, SettingsView
from utils import dbhandler, messagehandler
from utils.messagehandler import handle_gpt_response
from utils.pineconehandler import delete_namespace

# Constants
MAX_CHATBOTS = 20
SETTINGS_VIEW_TIMEOUT = 300
TIMEOUT_TIME = 60
ERROR_MESSAGE_CHATBOT_NOT_FOUND = "Please make sure you have entered the name correctly\nUse /listchatbots to see all created chatbots."
ERROR_MESSAGE_CHATBOT_DOES_NOT_EXIST = "Chatbot does not exist. Please check your spelling"
ROLEPLAY_INSTRUCTION = "Lets roleplay. During the roleplay, act as the character in the given description."
RESTARTING_MESSAGE = "Dis.AI is currently restarting for an update. We should be back soon; please try again in a few minutes!\n\nIf you keep seeing this error, please join the Community server."
BLUE_COLOUR = Colour.blue()


logger = logging.getLogger(__name__)
    
def trim_context(chatbot):
    while len(chatbot.context) > MEMORY_LENGTH:
        del chatbot.context[2:4]

def append_roleplay_context(chatbot, name, scenario_str):
    chatbot.context.append({'role':'system', 'content':f"{ROLEPLAY_INSTRUCTION} Only write one response as {name}.\n{scenario_str}"})

def append_prompt_context(chatbot, name, scenario_str):
    chatbot.context.append({'role':'system', 'content':f"{chatbot.prompt}\nWrite one response as {name}.\n{scenario_str}"})

async def handle_conversation_response(platform, chatbot, last_message, cost, interaction):
    response_success = await messagehandler.handle_gpt_response(platform, chatbot, last_message, credits_cost=cost, converse_mode=True, should_make_buttons=False)
    if response_success:
        platform.credits -= cost
        await asyncio.sleep(4)
    elif platform.credits <= 0:
        embed = await get_credits_needed_embed(chatbot, True)
        await interaction.channel.send(embed=embed)
        return False
    return True

async def do_conversation_mode(platform, interaction, scenario, chatbot1, chatbot2, last_message):
    """/conversation command. Starts a conversation between two chatbots."""
    try:
        scenario_str = f"Current scenario: {scenario}" if scenario else ""
        cost1 = helpers.get_credits_cost(chatbot1.model)
        cost2 = helpers.get_credits_cost(chatbot2.model)
        if last_message is None:
            last_message = await interaction.original_response()
            append_roleplay_context(chatbot1, chatbot1.name, scenario_str)
            append_roleplay_context(chatbot2, chatbot2.name, scenario_str)
            append_prompt_context(chatbot1, chatbot1.name, scenario_str)
            append_prompt_context(chatbot2, chatbot2.name, scenario_str)
        trim_context(chatbot1)
        trim_context(chatbot2)
        for i in range(2):
            if i == 1:
                append_roleplay_context(chatbot1, chatbot1.name, scenario_str)
                append_roleplay_context(chatbot2, chatbot2.name, scenario_str)
            if not await handle_conversation_response(platform, chatbot1, last_message, cost1, interaction):
                return
            chatbot2.context.append({'role':'user','content':chatbot1.context[-1]['content']})
            if not await handle_conversation_response(platform, chatbot2, last_message, cost2, interaction):
                return
            chatbot1.context.append({'role':'user','content':chatbot2.context[-1]['content']})
            last_message = chatbot2.last_message
        ContinueView = discord.ui.View()
        ContinueView.add_item(ContinueButton(platform, interaction, scenario, chatbot1, chatbot2, last_message))
        await chatbot2.last_message.edit(view=ContinueView)
    except Exception as e:
        logger.error(f"continue button err: {e}")
    
class ContinueButton(discord.ui.Button):
    """Button to continue the /conversation."""

    def __init__(self, platform, interaction, scenario, chatbot1, chatbot2, last_message):
        super().__init__(label="", style=discord.ButtonStyle.blurple, emoji="▶️")
        self.platform = platform
        self.interaction = interaction
        self.scenario = scenario
        self.chatbot1 = chatbot1
        self.chatbot2 = chatbot2
        self.last_message = last_message

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.last_message.edit(view=None)
            await interaction.response.defer()
            await do_conversation_mode(self.platform, self.interaction, self.scenario, self.chatbot1, self.chatbot2, self.last_message)
        except Exception as e:
            logger.error(f"continue button err: {e}")

class ConverseModal(discord.ui.Modal):
    """Modal to set up a conversation between chatbots."""

    def __init__(self, platform):
        super().__init__(title="Set up Conversation")
        self.platform = platform

    chatbot1 = discord.ui.TextInput(label="Chatbot 1 Name", style=discord.TextStyle.short, placeholder="Enter the name of an existing chatbot")
    chatbot2 = discord.ui.TextInput(label="Chatbot 2 Name", style=discord.TextStyle.short, placeholder="Enter the name of an existing chatbot")
    topic = discord.ui.TextInput(label="Topic", style=discord.TextStyle.long, placeholder="Chatbots will try to follow the topic. Example: Play by play superhero battle", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            chatbot1 = await self.get_chatbot_clone(self.chatbot1.value)
            chatbot2 = await self.get_chatbot_clone(self.chatbot2.value)
            chatbot1.mention_mode = False 
            chatbot1.data_name = ""
            chatbot1.context = []
            chatbot1.web_search = False 
            chatbot1.last_message = None
            chatbot1.long_term_memory = False
            chatbot2.mention_mode = False 
            chatbot2.data_name = ""
            chatbot2.context = []
            chatbot2.web_search = False 
            chatbot2.last_message = None
            chatbot2.long_term_memory = False
            if not chatbot1 or not chatbot2:
                await helpers.send_error_message("Please enter the names of existing chatbots. Double check your spelling.\nUse **/create** to create a chatbot and **/listchatbots** to show created chatbots.", interaction, True, None)
            await interaction.response.send_message(embed=discord.Embed(title="Conversation Start", color=discord.Color.blue(), description=f"Topic: {self.topic.value if self.topic.value else 'None chosen.'}"), content="")
            await do_conversation_mode(self.platform, interaction, self.topic.value, chatbot1, chatbot2, None)
        except Exception as e:
            logger.error(f"on submit converse err: {e}")

    async def get_chatbot_clone(self, name: str):
        """Fetch a chatbot by name."""
        chatbot = await dbhandler.get_cb(name, self.platform.chatbots)
        return await chatbot_clone(chatbot) if chatbot else None

class ChatBotSettings(commands.Cog):
    """Cog for chatbot settings."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("ChatBotSettings cog loaded.")

    @discord.app_commands.command(name="listchatbots", description="View all created chatbots")
    async def listchatbots(self, interaction: discord.Interaction) -> None:
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CHATBOTLIST.value)
            if not await helpers.has_correct_perms(platform, interaction):
                return
            embed = discord.Embed(title="List of chatbots", colour=Colour.blue())
            for bot in platform.chatbots:
                embed.add_field(name=bot.name, value="", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=TIMEOUT_TIME)
        except Exception as e:
            logger.error(f"chatbot list err: {e}")

    @discord.app_commands.command(name="create", description="Creates a new chatbot.")
    async def create(self, interaction: discord.Interaction) -> None:
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CHATBOTCREATE.value)
            if not await helpers.has_correct_perms(platform, interaction):
                return
            if len(platform.chatbots) > MAX_CHATBOTS:
                await helpers.send_error_message("You have too many chatbots! Delete some before you create more.", interaction)
                return
            await interaction.response.send_modal(CreateCBView(self.bot, platform))
        except Exception as e:
            logger.error(f"createcb err: {e}")
            await helpers.send_error_message("Dis.AI is currently restarting for an update. We should be back soon; please try again in a few minutes!\n\nIf you keep seeing this error, please join the Community server.", interaction, True)

    @discord.app_commands.command(name="settings", description="Change the settings for a chatbot")
    async def settings(self, interaction: discord.Interaction) -> None:
        try: 
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.SETTINGS.value)
            if not platform:
                logger.error(f"/settings err, probably restarting:")
                await helpers.send_error_message("Dis.AI is currently restarting for an update. We should be back soon; please try again in a few minutes!\n\nIf you keep seeing this error, please join the Community server.", interaction, True)
                return
            
            if not platform.chatbots:
                await helpers.send_error_message("No chatbots currently exist\nCreate a chatbot using ```/create```", interaction, True)
                return
            if not await helpers.has_correct_perms(platform, interaction):
                return
            await interaction.response.send_message(view=SettingsView(platform), delete_after=SETTINGS_VIEW_TIMEOUT)
        except Exception as e:
            logger.error(f"settings err: {e}")

    @discord.app_commands.command(name="chatbotinfo", description="View all settings for the specified chatbot")
    async def chatbotinfo(self, interaction: discord.Interaction, chatbot_name: str) -> None:
        platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CHATBOTINFO.value)
        if not await helpers.has_correct_perms(platform, interaction):
            return
        chatbot = await dbhandler.get_cb(name=chatbot_name, chatbots=platform.chatbots)
        if not chatbot:
            await helpers.send_error_message("Chatbot does not exist. Please make sure you have entered the name correctly.", interaction, True)
            return
        try:
            channels = [self.bot.get_channel(channel_id).name for channel_id in chatbot.channels]
            out = self.format_chatbot_info(chatbot, channels)
            await messagehandler.send_channel_msg_as_embed(interaction, out, title=f"Chatbot settings for {chatbot.name}", delete_after=TIMEOUT_TIME)
            await interaction.response.send_message(embed=discord.Embed(title="Chatbot settings above", color=Colour.blue()))
        except Exception as e:
            logger.error(e)

    def format_chatbot_info(self, chatbot, channels):
        """Format the chatbot info for display."""
        return f"{str(chatbot)}\n**Channels:** {', '.join(channels)}\n\nAll settings shown above can be changed.\nSee`/settings` for more details about each setting."

    @discord.app_commands.command(name="showenabledhere", description="Shows all chatbots that are enabled in the current channel")
    async def showenabledhere(self, interaction: discord.Interaction) -> None:
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.SHOWENABLEDHERE.value)
            if not await helpers.has_correct_perms(platform, interaction):
                return
            embed = discord.Embed(title="List of chatbots enabled in current channel", description="\n".join([chatbot.name for chatbot in platform.chatbots if interaction.channel.id in chatbot.channels]), colour=Colour.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=TIMEOUT_TIME)
        except Exception as e:
            logger.error(e)
        
    @discord.app_commands.command(name="enable", description = "Enables the specified chatbot in the current channel")
    async def enable(self, interaction: discord.Interaction, chatbot_name: str) -> None:
        """Enables the specified chatbot in the current channel."""
        try:
            platform = await self.get_platform(interaction)
            if not platform:
                await self.send_restarting_message(interaction)
                return
            if not await helpers.has_correct_perms(platform, interaction):
                return
            chatbot = await dbhandler.get_cb(name=chatbot_name, chatbots=platform.chatbots)
            if not chatbot:
                await helpers.send_error_message("Please make sure you have entered the name correctly\nUse `/listchatbots` to see all created chatbots.", interaction, True)
                return
            await self.enable_chatbot(interaction, platform, chatbot)
        except Exception as e:
            logging.error(e)

    async def get_platform(self, interaction: discord.Interaction):
        """Returns the platform for the given interaction."""
        try:
            return await helpers.get_platform(self.bot.platforms, interaction, Analytics.ENABLEHERE.value)
        except Exception as e:
            logging.error(f"/enable err, probably restarting: {e}")
            await self.send_restarting_message(interaction)

    async def send_restarting_message(self, interaction: discord.Interaction):
        """Sends a message indicating that the bot is restarting."""
        await helpers.send_error_message(RESTARTING_MESSAGE, interaction, True)

    async def enable_chatbot(self, interaction: discord.Interaction, platform, chatbot):
        """Enables the given chatbot on the given platform."""
        if interaction.channel.id not in chatbot.channels:
            await self.add_chatbot_to_channel(interaction, platform, chatbot)
        else:
            embed = discord.Embed(title=f"{chatbot.name} has already been added to this channel", description="Use `/disable` to disable.", colour=BLUE_COLOUR)
            await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=TIMEOUT_TIME)

    async def add_chatbot_to_channel(self, interaction: discord.Interaction, platform, chatbot):
        """Adds the given chatbot to the channel of the given interaction."""
        chatbot.channels.append(interaction.channel.id)
        await dbhandler.change_cb_setting_in_db(platform.id, chatbot.name, "channels", chatbot.channels)
        embed = discord.Embed(title=f"{chatbot.name} has been added to this channel", description=f"{chatbot.name} will now respond to messages in this channel.\nJust start chatting! ✨\n\nUse `/disable {chatbot.name}` to disable.", colour=BLUE_COLOUR)
        await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=TIMEOUT_TIME)
        await self.send_greeting(interaction, chatbot)

    async def send_greeting(self, interaction: discord.Interaction, chatbot):
        """Sends a greeting message from the given chatbot."""
        try:
            if chatbot.prompt.endswith("\n<START>\n") and not chatbot.context:
                chatbot.context.insert(0, {'role': 'system', 'content': chatbot.prompt})
                greeting = json.loads(chatbot.prompt[chatbot.prompt.find('{'):len(chatbot.prompt) - 9], strict=False)['first_mes']
                chatbot.context.insert(1, {'role': 'assistant', 'content': str(greeting)})
                await self.send_message(interaction, chatbot, greeting)
        except Exception as e:
            logging.error(e)

    async def send_message(self, interaction: discord.Interaction, chatbot, message):
        """Sends a message from the given chatbot."""
        if not isinstance(interaction.channel, discord.DMChannel):
            channel = interaction.channel.parent if isinstance(interaction.channel, discord.Thread) else interaction.channel
            webhooks = await channel.webhooks()
            for webhook in webhooks:
                if webhook.name == "Dis.AI Webhook":
                    og_webhook = webhook
                    break
            else:
                og_webhook = await channel.create_webhook(name="Dis.AI Webhook")
            if og_webhook:
                if isinstance(interaction.channel, discord.Thread):
                    await og_webhook.send(username=chatbot.name, wait=True, content=message, avatar_url=chatbot.avatar_url, thread=interaction.channel)
                else:
                    await og_webhook.send(username=chatbot.name, wait=True, content=message, avatar_url=chatbot.avatar_url)
            else:
                interaction.channel.send(content=str(message))
        else:
            interaction.channel.send(content=str(message))

    @discord.app_commands.command(name="disable", description="Disables the specified chatbot from the current channel.")
    async def disable(self, interaction: discord.Interaction, chatbot_name: str) -> None:
        """Disables the specified chatbot from the current channel."""
        platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.DISABLEHERE.value)
        if not await helpers.has_correct_perms(platform, interaction):
            return
        chatbot = await dbhandler.get_cb(name=chatbot_name, chatbots=platform.chatbots)
        if not chatbot:
            await helpers.send_error_message("Please make sure you have entered the name correctly\nUse /listchatbots to see all created chatbots.", interaction, True)
            return
        try:
            chatbot.channels.remove(interaction.channel.id)
            chatbot.bing_bots.pop(interaction.channel.id)
        except Exception as e:
            logging.error(e)
        await dbhandler.change_cb_setting_in_db(platform.id, chatbot.name, "channels", chatbot.channels)
        embed = discord.Embed(title=f"{chatbot.name} has been removed from the current channel", colour=BLUE_COLOUR)
        await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=TIMEOUT_TIME)
        
    @discord.app_commands.command(name="clearmemory", description="Clears the specified chatbot's memory. (Optional: choose # of messages to delete)")
    async def clearmemory(self, interaction: discord.Interaction, chatbot_name: str, number_of_messages_to_delete: int = -1) -> None:
        """Clears the memory of the specified chatbot."""
        platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CHATBOTCLEARMEMORY.value)
        if not await helpers.has_correct_perms(platform, interaction):
            return
        chatbot = await dbhandler.get_cb(name=chatbot_name, chatbots=platform.chatbots)
        if not chatbot:
            await helpers.send_error_message(ERROR_MESSAGE_CHATBOT_NOT_FOUND, interaction, True)
            return
        try:
            context_length = len(chatbot.context)
            if number_of_messages_to_delete <= 0:
                chatbot.context.clear()
                try:
                    await delete_namespace(f"{platform.id}-{chatbot.name}") # also clear long term memory
                    await delete_namespace(f"{platform.id}-{chatbot.name}-data")
                except Exception as e:
                    logger.error(f"Error while deleting namespace: {e}")
                embed = discord.Embed(title=f"🗑️  Cleared chat memory for {chatbot.name}", description=f"{context_length} messages deleted\nLong term memory has also been deleted", colour=Colour.blue())
                await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=TIMEOUT_TIME)
            else:   
                del chatbot.context[(-1 * number_of_messages_to_delete):]
                embed = discord.Embed(title=f"Cleared chat memory for {chatbot.name}  🗑️", description=f"{min(context_length, number_of_messages_to_delete)} messages deleted\nLong term memory not deleted", colour=Colour.blue())
                await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=TIMEOUT_TIME)
        except Exception as e:
            logger.error(f"clearmemory err: {e}")
            context_length = len(chatbot.context)
            chatbot.context.clear()
            try:
                await delete_namespace(f"{platform.id}-{chatbot.name}")
                await delete_namespace(f"{platform.id}-{chatbot.name}-data")
            except Exception as e:
                logger.error(f"Error while deleting namespace: {e}")
            embed = discord.Embed(title=f"🗑️  Cleared chat memory for {chatbot.name}", description=f"{context_length} messages deleted\bLong term memory also deleted", colour=Colour.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=TIMEOUT_TIME)

    @discord.app_commands.command(name="viewmemory", description="View the memory of the specified chatbot")
    async def viewmemory(self, interaction:discord.Interaction, chatbot_name: str) -> None:
        """Views the memory of the specified chatbot."""
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CHATBOTVIEWMEMORY.value)
            if not await helpers.has_correct_perms(platform, interaction):
                return
            chatbot = await dbhandler.get_cb(name=chatbot_name, chatbots=platform.chatbots)
            if not chatbot:
                await helpers.send_error_message(ERROR_MESSAGE_CHATBOT_NOT_FOUND, interaction, True)
                return
            out = ""
            for dict in chatbot.context:
                out += f"**{dict['role']}:** {dict['content']}\n"
            if not out:
                out = f"{chatbot.name}'s memory is empty."
            await messagehandler.send_channel_msg_as_embed(interaction, out, title=f"Chatbot memory for {chatbot.name}", delete_after=60)
            await interaction.response.send_message(embed=discord.Embed(title="Posted chatbot memory", color=discord.Colour.blue()))
        except Exception as e :
            logger.error(f"View mem err: {e}")
        
    @discord.app_commands.command(name="conversation", description="Make chatbots converse with each other")
    async def conversation(self, interaction: discord.Interaction) -> None:
        """Makes chatbots converse with each other."""
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction, Analytics.CONVERSE.value)
            if not await helpers.has_correct_perms(platform, interaction):
                return
            await interaction.response.send_modal(ConverseModal(platform))
        except Exception as e:
            logger.error(f"conversemode err: {e}")

    @discord.app_commands.command(name="forcemessage", description="Force a message from a chatbot")
    async def forcemessage(self, interaction: discord.Interaction, chatbot_name: str) -> None:
        """Forces a message from a chatbot."""
        try:
            platform = await helpers.get_platform(self.bot.platforms, interaction)
            chatbot = await dbhandler.get_cb(chatbot_name, platform.chatbots)
            if not chatbot:
                await helpers.send_error_message(ERROR_MESSAGE_CHATBOT_DOES_NOT_EXIST, interaction)
                return
            if not await helpers.has_correct_perms(platform, interaction):
                return
            await interaction.response.send_message(embed = discord.Embed(title="Forcing message", color=discord.Colour.blue()))
            original_response = await interaction.original_response()
            
            cost = helpers.get_credits_cost(chatbot.model)
            response_success = await handle_gpt_response(platform, chatbot, original_response, cost, None, False, chatbot.should_make_buttons, should_append_context=False)
            if response_success:
                platform.credits -= cost
        except Exception as e:
            logger.error(f"conversemode err: {e}")

async def setup(bot):
    await bot.add_cog(ChatBotSettings(bot))
