"""This file contains many of the UI elements for the bot."""

import logging
from typing import Optional

from discord import ui, Colour, Interaction

import discord

from extensions.constants import Analytics
from core.ChatBot import ChatBot, default_chat_bot
import utils.dbhandler as dbhandler
from extensions.embeds import (
    send_discord_invite, commands_help_embed, commands_help2_embed, 
    help_overview_embed, chatbot_settings_embed, chatbot_settings2_embed, 
    prompt_cb_embed
)
from extensions.helpers import get_platform_id, send_error_message, get_chatbot_settings_embed, update_analytics, get_prompt_library_embed, make_inviteview
from utils.pineconehandler import delete_namespace
import stripe
from config import (
    STRIPE_API_KEY, 
    APPLICATION_ID, 
    UPLOAD_DATA_COST, 
    TIER1AMOUNT, 
    TIER1PRICE, 
    TIER2AMOUNT, 
    TIER2PRICE, 
    TIER3AMOUNT, 
    TIER3PRICE, 
    CLAIM_CREDITS_AMOUNT, 
    VOTE_CREDITS_AMOUNT, 
    DISCORD_INVITE, 
    ICON_URL, 
    BOT_INVITE, 
    PROMPT1AVATAR,
    PROMPT1NAME, 
    PROMPT2AVATAR, 
    PROMPT2NAME, 
    PROMPT3AVATAR, 
    PROMPT3NAME, 
    PROMPT4AVATAR,
    PROMPT4NAME, 
    PROMPT5AVATAR, 
    PROMPT5NAME,
    jailbreak
)

# Define constants
MAX_NAME_LENGTH = 80
ASCII_LIMIT = 127
SELECT_CHATBOT = "Select Chatbot to Configure"
SELECT_SETTING_PAGE_1 = "Select Setting (Page 1)"
SELECT_SETTING_PAGE_2 = "Select Setting (Page 2)"
ERROR_MESSAGE = "An error occurred. Please join the support sever and contact the developer."
VALID_ROLES = ["assistant", "user", "system"]
ERROR_MESSAGE = "Enter a number between -2.0 and 2.0\n(Example: 0.7)"
BLUE_COLOUR = Colour.blue()
BUTTON_STYLE_GREEN = discord.ButtonStyle.green
BUTTON_STYLE_RED = discord.ButtonStyle.red
MIN_DROPDOWN_VALUES = 1
MAX_DROPDOWN_VALUES = 25
GPT_3_5_TURBO = "gpt-3.5-turbo"
GPT_4 = "gpt-4"
GPT_3_5_TURBO_16K = "gpt-3.5-turbo-16k"
GPT_4_COST = 20
GPT_3_5_TURBO_COST = 1
CLAIM_CREDITS_LABEL = "Claim 🪙 x{} (FREE)"
VOTE_CREDITS_LABEL = "Vote 🪙 x{} (FREE)"
BUY_CREDITS_LABEL = "Buy 🪙 x{} Credits (${})"
MAX_PROMPTS = 20
MAX_PROMPT_NAME_LENGTH = 60
newprompts_avatars = [(PROMPT1NAME, PROMPT1AVATAR),(PROMPT2NAME, PROMPT2AVATAR),(PROMPT3NAME, PROMPT3AVATAR),(PROMPT4NAME, PROMPT4AVATAR),(PROMPT5NAME, PROMPT5AVATAR)]

# Set up logging
logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = STRIPE_API_KEY

class CreateCBView(ui.Modal, title="Enter New Chatbot Name"):
    """Create a new chatbot from /create"""
    def __init__(self, bot, platform):
        self.bot = bot
        self.platform = platform
        super().__init__()

    name = ui.TextInput(label='Name', placeholder="Chatbot will respond with this name")
    avatar_url = ui.TextInput(label="Avatar URL", placeholder="(Optional) Chatbot will respond with this avatar", required=False)

    async def on_submit(self, interaction: Interaction):
        try:
            name = self.name.value.strip()
            for bot in self.platform.chatbots:
                if bot.name.strip().lower() == name.lower():
                    await send_error_message("A chatbot with this name already exists. Please delete that chatbot from `/settings` or pick a different name.\n\nUse `/listchatbots` to show all created chatbots.", interaction, send_invite=True)
                    return
            for char in name:
                if ord(char) > ASCII_LIMIT:
                    await send_error_message("Name must contain ASCII characters only.", interaction, send_invite=True)
                    return
            if len(name) > MAX_NAME_LENGTH:
                await send_error_message("Chatbot name is too long. Please try again with a shorter name.", interaction, send_invite=True)
                return

            newbot = await default_chat_bot(name=name)
            if self.avatar_url.value:
                newbot.avatar_url = self.avatar_url.value.strip()
            await interaction.response.send_message(embed=prompt_cb_embed, view=PromptView(self.platform, newbot, createcb_mode=True))
        except Exception as error:
            logger.error(f"createcb modal err: {error}")
            raise


class SettingsView(discord.ui.View):
    """View for the /settings command"""
    def __init__(self, platform):
        super().__init__()
        
        chatbotdropdown = ChatbotDropdown(platform)
        editbutton = EditButton(platform, chatbotdropdown)
        deletebutton = DeleteButton(platform.chatbots, chatbotdropdown, platform)
        self.add_item(chatbotdropdown)
        self.add_item(editbutton)
        self.add_item(deletebutton)
        
class EditButton(ui.Button):
    """/settings button to configure a chatbot's settings"""
    def __init__(self, platform, chatbotdropdown):
        super().__init__(label="Configure", style=BUTTON_STYLE_GREEN)
        self.platform = platform
        self.chatbotdropdown = chatbotdropdown
        
    async def callback(self, interaction: discord.Interaction):
        try:
            if self.chatbotdropdown.chatbot:
                view = discord.ui.View()
                view.add_item(SettingsListDropdown(self.platform, self.chatbotdropdown.chatbot))
                view.add_item(RightSettingsButton(self.platform, self.chatbotdropdown.chatbot))
                view.add_item(BackToChatbotSelectionButton(self.platform))
                embed = get_chatbot_settings_embed(self.chatbotdropdown.chatbot.name, 1)
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.defer()
        except Exception as e:
            print(f"edit button err: {e}")
            
class BackToChatbotSelectionButton(ui.Button):
    """Return to chatbot selection button"""
    def __init__(self, platform):
        super().__init__(label="Back to Chatbot Select", style=discord.ButtonStyle.grey)
        self.platform = platform   
    
    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(embed=None, view=SettingsView(self.platform))
        except Exception as e:
            print(f"back to chatbot select err: {e}")   

class RightSettingsButton(ui.Button):
    """/settings button that goes to page 2"""
    def __init__(self, platform, chatbot):
        super().__init__(label="Page 2 ->", style=discord.ButtonStyle.green)
        self.platform = platform
        self.chatbot = chatbot
        
    async def callback(self, interaction: discord.Interaction):
        try:
            view = discord.ui.View()
            view.add_item(SettingsListDropdown2(self.platform, self.chatbot))
            view.add_item(LeftSettingsButton(self.platform, self.chatbot))
            embed = get_chatbot_settings_embed(self.chatbot.name, 2)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(e)
            
class LeftSettingsButton(ui.Button):
    """/settings button that goes back to page 1"""
    def __init__(self, platform, chatbot):
        super().__init__(label="<- Page 1", style=discord.ButtonStyle.green)
        self.platform = platform
        self.chatbot = chatbot
        
    async def callback(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(SettingsListDropdown(self.platform, self.chatbot))
        view.add_item(RightSettingsButton(self.platform, self.chatbot))
        embed = get_chatbot_settings_embed(self.chatbot.name, 1)
        await interaction.response.edit_message(embed=embed, view=view)
            
class DeleteButton(ui.Button):
    """Button for deleting a chatbot from the platform's chatbot list"""
    def __init__(self, chatbots, chatbotdropdown, platform):
        super().__init__(label="Delete", style=discord.ButtonStyle.red)
        self.chatbots = chatbots
        self.chatbotdropdown = chatbotdropdown
        self.platform = platform

    async def callback(self, interaction: Interaction):
        try:
            if self.chatbotdropdown.chatbot:
                if len(self.platform.chatbots) >= 2:
                    try:
                        await delete_namespace(f"{self.platform.id}-{self.chatbotdropdown.chatbot.name}")
                        await delete_namespace(f"{self.platform.id}-{self.chatbotdropdown.chatbot.name}-data")
                    except Exception as error:
                        logger.error(f"Failed to delete namespace: {error}")
                        raise
                    await dbhandler.remove_cb_from_db(self.platform.id, self.chatbotdropdown.chatbot.name)
                    self.chatbots.remove(self.chatbotdropdown.chatbot)
                    embed = discord.Embed(title=f"Deleted chatbot: {self.chatbotdropdown.chatbot.name}", colour=Colour.blue())
                    view = ui.View()
                    view.add_item(BackToChatbotSelectionButton(self.platform))

                    await interaction.response.edit_message(view=view, embed=embed)
                else:
                    view = ui.View()
                    view.add_item(BackToChatbotSelectionButton(self.platform))
                    await send_error_message("You must have at least one chatbot.\nCreate another chatbot before you delete this one!", interaction, view=view)
            else:
                await interaction.response.defer()
        except Exception as error:
            logger.error(f"Delete chatbot err: {error}")
            raise            
        
class ChatbotDropdown(ui.Select):
    """Dropdown for selecting a chatbot from /settings."""
    def __init__(self, platform):
        options = [discord.SelectOption(label=chatbot.name) for chatbot in platform.chatbots]
        super().__init__(placeholder=SELECT_CHATBOT, options=options, min_values=MIN_DROPDOWN_VALUES, max_values=MIN_DROPDOWN_VALUES)
        self.chatbot = None
        self.chatbots = platform.chatbots

    async def callback(self, interaction: discord.Interaction):
        try:
            self.chatbot = await dbhandler.get_cb(str(self.values[0]), self.chatbots)
            await interaction.response.defer()
        except Exception as error:
            logger.error(error)

class SettingsListDropdown(ui.Select):
    """Dropdown for selecting a setting (page 1)."""
    def __init__(self, platform, chatbot):
        self.platform = platform
        self.chatbot = chatbot
        self.backview = BackToSelectionView(self.chatbot, self.platform)
        options = [
            discord.SelectOption(label="📚  Prompt Library  📚"),
            discord.SelectOption(label="➕ Add Long Prompt"),
            discord.SelectOption(label="✏️ Edit Avatar"),
            discord.SelectOption(label="👥 Include Usernames"),
            discord.SelectOption(label="📄/🎥 PDF / YouTube Video"),
            discord.SelectOption(label="📣 Mention Mode"),
            discord.SelectOption(label="🧠 Long Term Memory"),
            discord.SelectOption(label="🌐 Web Search"),
            discord.SelectOption(label="🔄 Toggle reactions"),
            discord.SelectOption(label="📖 Lorebooks")
        ]
        super().__init__(placeholder=SELECT_SETTING_PAGE_1, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.handle_selection(interaction)
        except Exception as error:
            logger.error(f"In selection stuff, prompt err {error}")

    async def handle_selection(self, interaction):
        match self.values[0]:
            case "📚  Prompt Library  📚":
                try:
                    await update_analytics(self.platform.analytics, Analytics.PROMPT.value)
                    embed=get_prompt_library_embed(self.chatbot.name)
                    await interaction.response.edit_message(embed=embed, view=PromptView(self.platform, self.chatbot))
                except Exception as e:
                    print(f"in selection stuff, prompt err {e}")
            case "👥 Include Usernames":
                await update_analytics(self.platform.analytics, Analytics.INCLUDEUSERNAMES.value)
                await interaction.response.edit_message(embed=discord.Embed(title="Include Usernames", description="Allows chatbots to understand usernames", color=discord.Colour.blue()), view=IUMenu(self.chatbot, self.backview))
                # await interaction.followup.send(
            case "📄/🎥 PDF / YouTube Video":
                try:
                    await update_analytics(self.platform.analytics, Analytics.PDFORVIDEO.value)
                    name = "PDF / Youtube Video: None" if not self.chatbot.data_name else self.chatbot.data_name
                    await interaction.response.edit_message(view=AddDataView(self.chatbot, self.platform, self.backview), embed=discord.Embed(title=f"Current {name}", color=discord.Colour.blue()))
                except Exception as e:
                    print(e)
            case "✏️ Edit Avatar":
                await interaction.response.send_modal(EditAvatarModal(self.chatbot, self.backview))
            case "📣 Mention Mode":
                try:
                    await update_analytics(self.platform.analytics, Analytics.MENTIONMODE.value)
                    await interaction.response.defer()
                    await interaction.followup.edit_message(interaction.message.id, view=MentionModeView(self.chatbot, self.backview), embed=discord.Embed(title="Mention Mode Settings", description=f"If Mention Mode is enabled, the chatbot will only respond if <@{APPLICATION_ID}> is mentioned.\nThe chatbot will still respond with context as long as it is enabled in the channel.", color=discord.Colour.blue()))
                except Exception as e:
                    print(e)
            case "🧠 Long Term Memory":
                await update_analytics(self.platform.analytics, Analytics.LONGTERMMEMORY.value)
                await interaction.response.edit_message(view=LTMView(self.chatbot, self.backview))
            case "🌐 Web Search":
                await update_analytics(self.platform.analytics, Analytics.WEBSEARCH.value)
                await interaction.response.edit_message(view=WebSearchView(self.chatbot, self.backview), embed=discord.Embed(title="Web Search settings", description="If enabled, chatbots will automatically perform web searches when appropriate. Web searches take longer. Disable if you don't want this.", color=discord.Colour.blue()))
            case "➕ Add Long Prompt":
                try:
                    await update_analytics(self.platform.analytics, Analytics.LONGPROMPT.value)
                    if len(self.platform.prompts) > 20:
                        await send_error_message("Too many prompts have been added (> 20)\nPlease delete some prompts from the prompt library before adding more.", interaction, view=self.backview)
                    embed=discord.Embed(title="Long Prompt: Attach text file with your prompt below", description="Allows you to bypass Discord's 2000 character limit.", color=discord.Colour.blue())
                    self.platform.waiting_for = "Long Prompt"
                    self.platform.current_cb = self.chatbot
                    await interaction.response.send_message(embed=embed)
                except Exception as e:
                    print(f"Long prompt error: {e}")
            case "🔄 Toggle reactions":
                await update_analytics(self.platform.analytics, Analytics.REGENERATEORCONTINUEBUTTONS.value)
                await interaction.response.edit_message(embed=discord.Embed(title="Toggle reactions", description="Toggle the regenerate, continue, and delete reactions that appear at the end of chatbot messages.", color=discord.Colour.blue()), view=ReactionButtonsView(self.chatbot, self.backview))
            case "📖 Lorebooks":
                try:
                    await update_analytics(self.platform.analytics, Analytics.LOREBOOKS.value)
                    lorebook_str = '\n'.join(self.chatbot.lorebooks)
                    if self.chatbot.lorebooks:
                        desc_str = f"Current lorebooks:\n{lorebook_str}"
                    else:
                        desc_str = "No lorebooks have been added yet. Add one below!"
                    await interaction.response.edit_message(embed=discord.Embed(title=f"{self.chatbot.name}'s lorebooks", description=desc_str, color = discord.Colour.blue()), view=LorebookView(self.platform, self.chatbot))
                except Exception as e:
                    logger.error(f"Error in lorebooks: {e}")
            case _:
                await send_error_message("An error occurred. Please join the support sever and contact the developer.", interaction, send_invite=True)
        

class SettingsListDropdown2(ui.Select):
    """Dropdown for selecting a setting (page 2)."""
    def __init__(self, platform, chatbot):
        self.platform = platform
        self.chatbot = chatbot
        self.backview = BackToSelectionView(self.chatbot, self.platform)
        options = [
            discord.SelectOption(label="🤖 GPT Model"),
            discord.SelectOption(label="💉 Inject Message"),
            discord.SelectOption(label="🔧 Temperature"),
            discord.SelectOption(label="🔧 Presence Penalty"),
            discord.SelectOption(label="🔧 Frequency Penalty"),
            discord.SelectOption(label="🔧Top P")
        ]
        super().__init__(placeholder=SELECT_SETTING_PAGE_2, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.handle_selection(interaction)
        except Exception as error:
            logger.error(f"Settings dropdown2 err: {error}")

    async def handle_selection(self, interaction):
        try:
            match self.values[0]:
                case "🤖 GPT Model":
                    await update_analytics(self.platform.analytics, Analytics.AIMODEL.value)
                    await interaction.response.edit_message(view=ChangeModelView(self.chatbot, self.platform, self.backview))
                case "💉 Inject Message":
                    await update_analytics(self.platform.analytics, Analytics.INJECTMESSAGE.value)
                    await interaction.response.send_modal(IJModal(self.chatbot, self.backview))
                case "🔧 Temperature":
                    await update_analytics(self.platform.analytics, Analytics.TEMPERATURE.value)
                    await interaction.response.send_modal(TempModal(self.chatbot, self.backview))
                case "🔧 Presence Penalty":
                    await update_analytics(self.platform.analytics, Analytics.PP.value)
                    await interaction.response.send_modal(PPModal(self.chatbot, self.backview))
                case "🔧 Frequency Penalty":
                    await update_analytics(self.platform.analytics, Analytics.FP.value)
                    await interaction.response.send_modal(FPModal(self.chatbot, self.backview))
                case "🔧Top P":
                    await update_analytics(self.platform.analytics, Analytics.TOPP.value)
                    await interaction.response.send_modal(TopPModal(self.chatbot, self.backview))
                case _:
                    await send_error_message("An error occurred. Please join the support sever and contact the developer.", interaction, send_invite=True)
        except Exception as e:
            print(f"settings drop2 err: {e}")

class IJModal(ui.Modal):
    """Modal for entering a message to inject."""
    def __init__(self, chatbot, backview):
        super().__init__(title="Enter Message to Inject")
        self.chatbot = chatbot
        self.backview = backview

    content = ui.TextInput(label="Message", style=discord.TextStyle.long, placeholder="user: Where are we?\nsystem: We're in York's Castle.\nassistant: Why, York's Castle, of course!")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.handle_submit(interaction)
        except ValueError as error:
            logger.error(error)

    async def handle_submit(self, interaction: discord.Interaction):
        lines = self.content.value.strip().split("\n")
        lines_added = 0
        for line in lines:
            role, content = line.split(":", 1)
            role = role.strip().lower()
            if role in VALID_ROLES: 
                self.chatbot.context.append({'role': role, 'content': content.strip()})
                lines_added += 1
            else:
                await self.send_error_message(interaction, lines_added)
                
        lines = self.content.value.strip().split('\n')
        result = []
        current_role = None
        current_content = []
        
        for line in lines: # split content into {'role': role, 'content': content} dicts
            if line.startswith('user:'):
                if current_role is not None:
                    result.append({'role': current_role, 'content': ' '.join(current_content)})
                current_role = 'user'
                current_content = [line[5:].strip()]
            elif line.startswith('assistant:'):
                if current_role is not None:
                    result.append({'role': current_role, 'content': ' '.join(current_content)})
                current_role = 'assistant'
                current_content = [line[10:].strip()]
            elif line.startswith('system:'):
                if current_role is not None:
                    result.append({'role': current_role, 'content': ' '.join(current_content)})
                current_role = 'system'
                current_content = [line[7:].strip()]
            else:
                current_content.append(line.strip())
        
            if current_role is not None:
                self.chatbot.context.append({'role': current_role, 'content': ' '.join(current_content)})

        
        embed = discord.Embed(title="Successfully Injected Message", description=f"Injected messages into {self.chatbot.name}'s chat history", color=discord.Colour.blue())
        await interaction.response.edit_message(embed=embed, view=self.backview)

    async def send_error_message(self, interaction, lines_added):
        embed = discord.Embed(title="Error", description="Invalid role entered\nPossible roles: \"system\", \"assistant\", or \"user\"\nMessages must be in format:\nrole: message\nrole:message", color=discord.Colour.blue())
        if lines_added != 0:
            del self.chatbot.context[-1 * lines_added:]
        await interaction.response.edit_message(embed=embed, view=self.backview)


class ParameterModal(ui.Modal):
    """Modal for changing a numeric parameter of the chatbot. (temperature, presence penalty, etc.)"""
    def __init__(self, chatbot, backview, title, min_val, max_val, placeholder):
        super().__init__(title=title)
        self.chatbot = chatbot
        self.backview = backview
        self.min_val = min_val
        self.max_val = max_val
        self.placeholder = placeholder
        self.response = ui.TextInput(label="", style=discord.TextStyle.short, placeholder=self.placeholder)
        self.add_item(self.response)
    async def on_submit(self, interaction: discord.Interaction):
        if ChatBot.validate_input(int(self.response.value), self.min_val, self.max_val):
            if self.title.endswith("Temperature"):
                self.chatbot.temperature = float(self.response.value)
            elif self.title.endswith("Presence Penalty"):
                self.chatbot.presence_penalty = float(self.response.value)
            elif self.title.endswith("Frequency Penalty"):
                self.chatbot.frequency_penalty = float(self.response.value)
            elif self.title.endswith("Top P"):
                self.chatbot.top_p = float(self.response.value)
            embed = discord.Embed(title=f"{self.title} changed for chatbot: {self.chatbot.name}", description="Changed to:", color=discord.Colour.blue())
            embed.add_field(name="", value=self.response.value)
            await interaction.response.edit_message(embed=embed, view=self.backview)
        else:
            await send_error_message(self.placeholder, interaction, view=self.backview)

    def get_components(self):
        return [self.response]

class TempModal(ParameterModal):
    def __init__(self, chatbot, backview):
        super().__init__(chatbot, backview, "Enter New Temperature", 0, 2, "Enter a number between 0.0 and 2.0 (Ex. 0.9)")


class PPModal(ParameterModal):
    def __init__(self, chatbot, backview):
        super().__init__(chatbot, backview, "Enter New Presence Penalty", -2, 2, "Enter a number between -2.0 and 2.0 (Ex. 0.7)")


class FPModal(ParameterModal):
    def __init__(self, chatbot, backview):
        super().__init__(chatbot, backview, "Enter New Frequency Penalty", -2, 2, "Enter a number between -2.0 and 2.0 (Ex. 0.7)")

class TopPModal(ParameterModal):
    def __init__(self, chatbot, backview):
        super().__init__(chatbot, backview, "Enter New Top P", 0, 1, "Enter a number between 0.0 and 1.0 (Ex. 0.7)")
        
class AdminRoleView(ui.View):
    """View for setting Admin Roles"""
    def __init__(self, server):
        super().__init__()
        self.add_item(AddAdminRoleButton(server, self))
        self.add_item(RemoveAdminRoleButton(server, self))


class AddAdminRoleButton(ui.Button):
    """Button to Add Admin Role"""
    def __init__(self, server, view):
        super().__init__(label="Add Role", style=discord.ButtonStyle.green, custom_id="add")
        self.original_view = view
        self.server = server

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(embed=None, view=AddAdminRoleView(self.server, self.original_view))


class RemoveAdminRoleButton(ui.Button):
    """Button to Remove Admin Role"""
    def __init__(self, server, view):
        super().__init__(label="Remove Role", style=discord.ButtonStyle.red, custom_id="remove")
        self.original_view = view
        self.server = server

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(embed=None, view=RemoveAdminRoleView(interaction, self.server, self.original_view))


class AddAdminRoleView(ui.View):
    """View to Add Admin Role"""
    def __init__(self, server, view):
        super().__init__()
        self.add_item(AddAdminRoleDropdown(server, view))


class AddAdminRoleDropdown(ui.RoleSelect):
    """Dropdown to Add Admin Role"""
    def __init__(self, server, view):
        self.server = server
        self.original_view = view
        super().__init__(placeholder="Select roles to set as Admin", min_values=MIN_DROPDOWN_VALUES, max_values=MAX_DROPDOWN_VALUES)

    async def callback(self, interaction: Interaction):
        await self.server.set_admin_roles([role.id for role in self.values])
        out = "\n".join([role.name for role in self.values])
        embed = discord.Embed(title="Admin roles set", description=f"Only members with the following roles can change the settings of Dis.AI chatbots:\n{out}", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=None, embed=embed)


class RemoveAdminRoleView(ui.View):
    """View to Remove Admin Role"""
    def __init__(self, interaction, server, view):
        super().__init__()
        self.add_item(RemoveAdminRoleDropdown(interaction, server, view))


class RemoveAdminRoleDropdown(ui.Select):
    """Dropdown to Remove Admin Role"""
    def __init__(self, interaction, server, view):
        options = [discord.SelectOption(label=interaction.guild.get_role(role_id).name) for role_id in server.adminroles]
        self.server = server
        self.original_view = view
        super().__init__(placeholder="Select Admin Role(s) to Remove", options=options, min_values=MIN_DROPDOWN_VALUES, max_values=len(options))

    async def callback(self, interaction: Interaction):
        adminroles = [interaction.guild.get_role(role_id) for role_id in self.server.adminroles]
        for role in adminroles:
            if role.name in self.values:
                self.server.adminroles.remove(role.id)
        out = "\n".join([role_name for role_name in self.values])
        if len(self.server.adminroles) == 0:
            embed = discord.Embed(title="Removed admin roles", description="All admin roles have been removed. All members can now change the settings of Dis.AI chatbots.", color=BLUE_COLOUR)
        else:
            embed = discord.Embed(title="Removed admin roles", description=f"Members with the following roles can no longer change the settings of Dis.AI chatbots:\n{out}", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=None, embed=embed)

# cb stands for chatbot
class ChangeModelView(ui.View):
    """View for changing the model of the chatbot."""
    
    def __init__(self, chatbot, server, back_view):
        super().__init__()
        self.add_item(ChangeModelDropdown(chatbot, server, back_view))
        self.add_item(BackToSelectionButton(chatbot, back_view.platform))

class ChangeModelDropdown(ui.Select):
    """Dropdown for selecting the model of the chatbot."""
    
    def __init__(self, chatbot, server, back_view):
        self.chatbot = chatbot
        self.server = server
        self.back_view = back_view
        options = [discord.SelectOption(label=GPT_3_5_TURBO), discord.SelectOption(label=GPT_3_5_TURBO_16K), discord.SelectOption(label=GPT_4)]
        super().__init__(placeholder="Select Model", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        """Handle the selection of a model."""
        
        self.disabled = True
        selected_model = self.values[0]
        
        additional_cost = ""
        if selected_model == GPT_4:
            self.chatbot.model = GPT_4
            cost = GPT_4_COST
            desc_str = f"Note: {selected_model} responses cost 🪙 x{cost} credits per response!"
        elif selected_model == GPT_3_5_TURBO:
            self.chatbot.model = GPT_3_5_TURBO
            cost = GPT_3_5_TURBO_COST
            desc_str = f"Note: {selected_model} responses cost 🪙 x{cost} credits per response!"
        elif selected_model == GPT_3_5_TURBO_16K:
            self.chatbot.model = GPT_3_5_TURBO_16K
            cost = GPT_3_5_TURBO_16K
            desc_str = f"Note: GPT-3.5-Turbo-16k responses cost 🪙 x2 credits per response **AND 🪙 +1 credit for every 1000 tokens in your chatbot's memory after it has reached 4000 tokens.** Ex. if there are 5000 tokens in memory, the response will cost 3 credits.\nUse `/chatbotinfo` to view the amount of tokens in your chatbot's memory."
        embed = discord.Embed(
            title="Successfully set model", 
            description=f"Model for {self.chatbot.name} has been set to {selected_model}\n{desc_str}",
            colour=Colour.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self.back_view)

        
class IUMenu(discord.ui.View):
    """Menu for enabling or disabling the inclusion of usernames."""
    
    def __init__(self, chatbot, back_view):
        super().__init__()
        self.chatbot = chatbot 
        self.back_view = back_view
        self.add_item(BackToSelectionButton(chatbot, back_view.platform))
    
    @discord.ui.button(label="Enabled", style=discord.ButtonStyle.green)
    async def enable_usernames(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable the inclusion of usernames."""
        
        self.chatbot.include_usernames = True
        embed = self._create_embed(f"Include usernames enabled for {self.chatbot.name}", discord.Colour.blue())
        await interaction.response.edit_message(view=self.back_view, embed=embed)
        
    @discord.ui.button(label="Disabled", style=discord.ButtonStyle.red)
    async def disable_usernames(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Disable the inclusion of usernames."""
        
        self.chatbot.include_usernames = False
        embed = self._create_embed(f"Include usernames disabled for {self.chatbot.name}", discord.Colour.red())
        await interaction.response.edit_message(view=self.back_view, embed=embed)
            
    def _create_embed(self, title, color):
        """Create an embed with the given title and color."""
        
        return discord.Embed(title=title, color=color)

class WebSearchView(discord.ui.View):
    """View for enabling or disabling web search. /settings."""
    def __init__(self, chatbot, back_view):
        super().__init__()
        self.chatbot = chatbot
        self.back_view = back_view
        self.add_item(BackToSelectionButton(chatbot, back_view.platform))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def enable_web_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable web search."""
        
        self.chatbot.web_search = True
        embed = discord.Embed(title=f"Web search enabled for {self.chatbot.name}", color=discord.Colour.blue())
        await interaction.response.edit_message(embed=embed, view=self.back_view)
        
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.red)
    async def disable_web_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Disable web search."""
        
        self.chatbot.web_search = False
        embed = discord.Embed(title=f"Web search disabled for {self.chatbot.name}", color=discord.Colour.red())
        await interaction.response.edit_message(embed=embed, view=self.back_view)

class LTMView(discord.ui.View):
    """View for managing long term memory."""
    
    def __init__(self, chatbot, back_view):
        super().__init__()
        self.chatbot = chatbot
        self.back_view = back_view
        self.add_item(BackToSelectionButton(chatbot, back_view.platform))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def enable_ltm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable long term memory."""
        
        self.chatbot.long_term_memory = True
        embed = self._create_embed(f"Long term memory enabled for {self.chatbot.name}", discord.Colour.blue())
        await interaction.response.edit_message(embed=embed, view=self.back_view)
        
    @discord.ui.button(label="Disable", style=discord.ButtonStyle.red)
    async def disable_ltm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Disable long term memory."""
        
        self.chatbot.long_term_memory = False
        embed = self._create_embed(f"Long term memory disabled for {self.chatbot.name}", discord.Colour.red())
        await interaction.response.edit_message(embed=embed, view=self.back_view)

    @discord.ui.button(label="Clear Long Term Memory", style=discord.ButtonStyle.blurple)
    async def clear_ltm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Clear long term memory."""
        
        try:
            await delete_namespace(f"{get_platform_id(interaction)}-{self.chatbot.name}")
            await delete_namespace(f"{get_platform_id(interaction)}-{self.chatbot.name}-data")
        except Exception as e:
            print(f"Error while deleting namespace: {e}")
        else:
            self.chatbot.batch_number = 0
            embed = self._create_embed(f"All long term memory cleared for {self.chatbot.name}", discord.Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.back_view)

    def _create_embed(self, title, color):
        """Create an embed with the given title and color."""
        
        return discord.Embed(title=title, color=color)


class BaseView(ui.View):
    """Base class for views that just have enable and disable buttons."""

    def __init__(self, chatbot, backview):
        super().__init__()
        self.chatbot = chatbot
        self.backview = backview
        self.add_item(BackToSelectionButton(self.chatbot, backview.platform))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        raise NotImplementedError

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.red)
    async def disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        raise NotImplementedError

class AddDataView(ui.View):
    """View for adding data."""
    def __init__(self, chatbot, platform, backview):
        super().__init__()
        self.chatbot = chatbot
        self.backview = backview
        self.platform = platform
        self.add_item(BackToSelectionButton(self.chatbot, backview.platform))


    @discord.ui.button(label=f"Set New PDF / Video (🪙 x{UPLOAD_DATA_COST} credits)", style=discord.ButtonStyle.green)
    async def enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.platform.waiting_for = "data"
        self.platform.current_cb = self.chatbot
        await interaction.response.edit_message(view=self.backview, embed=discord.Embed(title="Paste link to PDF or YouTube Video", description="You may also upload PDF files directly.", color=BLUE_COLOUR))


    @discord.ui.button(label="Remove Current PDF / Video", style=discord.ButtonStyle.red)
    async def disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await delete_namespace(f"{self.platform.id}-{self.chatbot.name}-data")
        except Exception as e:
            logging.error(f"AddDataView tried to delete namespace but failed: {e}")
        if self.chatbot.data_name:
            embed = discord.Embed(title=f"{self.chatbot.data_name} has been removed from memory", color=BLUE_COLOUR)
            self.chatbot.data_name = ""
        else:
            embed = discord.Embed(title="No PDF / Video has been uploaded.", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=self.backview, embed=embed)
class MentionModeView(BaseView):
    """View for mention mode."""
    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chatbot.mention_mode = True
        embed = discord.Embed(title="Mention Mode enabled", description=f"{self.chatbot.name} will now only respond to messages (with context) if <@{APPLICATION_ID}> is mentioned.", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=self.backview, embed=embed)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.red)
    async def disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chatbot.mention_mode = False
        embed = discord.Embed(title="Mention Mode disabled", description=f"{self.chatbot.name} will now respond to messages even if <@{APPLICATION_ID}> is not mentioned.", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=self.backview, embed=embed)


class ReactionButtonsView(BaseView):
    """View for reaction buttons setting from /settings."""

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.green)
    async def enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chatbot.should_make_buttons = True
        embed = discord.Embed(title="Reactions enabled", description=f"{self.chatbot.name} will have regenerate, continue, and delete buttons appear at the end of messages.", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=self.backview, embed=embed)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.red)
    async def disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chatbot.should_make_buttons = False
        embed = discord.Embed(title="Reactions disabled", description=f"{self.chatbot.name} will no longer have regenerate, continue, and delete buttons appear at the end of messages.", color=BLUE_COLOUR)
        await interaction.response.edit_message(view=self.backview, embed=embed)



def create_stripe_product(name, price):
    """Create a stripe product and price."""
    product = stripe.Product.create(name=name)
    price = stripe.Price.create(currency='usd', unit_amount=price, product=product.id)
    return product, price

TIER1_NAME = f"Dis.AI - {TIER1AMOUNT} Credits"
TIER2_NAME = f"Dis.AI - {TIER2AMOUNT} Credits"
TIER3_NAME = f"Dis.AI - {TIER3AMOUNT} Credits"

credits_tier1, credits_tier1_price = create_stripe_product(TIER1_NAME, TIER1PRICE)
credits_tier2, credits_tier2_price = create_stripe_product(TIER2_NAME, TIER2PRICE)
credits_tier3, credits_tier3_price = create_stripe_product(TIER3_NAME, TIER3PRICE)

async def get_checkout_url(user_id, platform_id, channel_id, price_id, credits):
    """Get the checkout URL."""
    id_dict = {"user_id": user_id, "platform_id": platform_id, "channel_id": channel_id, "credits": credits}
    session = stripe.checkout.Session.create(
        success_url="https://discord.gg/YfA9NwNNQV",
        payment_method_types=['card'],
        client_reference_id=str(id_dict),
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment"
    )
    return session['url']


class CreditsView(discord.ui.View):
    """View for displaying credits options."""

    def __init__(self, platform: str):
        super().__init__()
        self.platform = platform
        self.add_item(VoteButton(platform, True))
        self.add_item(CreditsDropdown(self, platform))

class CreditsDropdown(discord.ui.Select):
    """Dropdown for selecting credits options."""

    def __init__(self, view: discord.ui.View, platform: str):
        self.ogview = view
        self.platform = platform
        options = [
            discord.SelectOption(label=CLAIM_CREDITS_LABEL.format(CLAIM_CREDITS_AMOUNT), description="Join our Community Server and /claim (every 12 hours)"), 
            discord.SelectOption(label=VOTE_CREDITS_LABEL.format(VOTE_CREDITS_AMOUNT), description="Vote for us on Top.GG (every 12 hours)"), 
            discord.SelectOption(label=BUY_CREDITS_LABEL.format(TIER1AMOUNT, TIER1PRICE / 100), description="Buy and get credits instantly"), 
            discord.SelectOption(label=BUY_CREDITS_LABEL.format(TIER2AMOUNT, TIER2PRICE / 100), description="Buy and get credits instantly"), 
            discord.SelectOption(label=BUY_CREDITS_LABEL.format(TIER3AMOUNT, TIER3PRICE / 100), description="Buy and get credits instantly"), 
        ]
        super().__init__(placeholder="Select Option", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        """Handle selection from dropdown."""
        try:
            if self.values[0] == CLAIM_CREDITS_LABEL.format(CLAIM_CREDITS_AMOUNT):
                await self.update_analytics_and_add_button(interaction, Analytics.CREDITSCLAIM.value, ClaimButton)
            elif self.values[0] == VOTE_CREDITS_LABEL.format(VOTE_CREDITS_AMOUNT):
                await self.update_analytics_and_add_button(interaction, Analytics.CREDITSVOTE.value, VoteButton)
            elif self.values[0] == BUY_CREDITS_LABEL.format(TIER1AMOUNT, TIER1PRICE / 100):
                await self.update_analytics_and_add_button(interaction, Analytics.TIER1CREDITS.value, CreditsButton, TIER1AMOUNT, credits_tier1_price)
            elif self.values[0] == BUY_CREDITS_LABEL.format(TIER2AMOUNT, TIER2PRICE / 100):
                await self.update_analytics_and_add_button(interaction, Analytics.TIER2CREDITS.value, CreditsButton, TIER2AMOUNT, credits_tier2_price)
            elif self.values[0] == BUY_CREDITS_LABEL.format(TIER3AMOUNT, TIER3PRICE / 100):
                await self.update_analytics_and_add_button(interaction, Analytics.TIER3CREDITS.value, CreditsButton, TIER3AMOUNT, credits_tier3_price)
        except Exception as e:
            logging.error(f"Credits dropdown callback error: {e}")

    async def update_analytics_and_add_button(self, interaction, analytics, button_class, amount=None, price=None):
        """Update analytics and add button to view."""
        await update_analytics(self.platform.analytics, analytics)
        if amount and price:
            url = await get_checkout_url(interaction.user.id, self.platform.id, interaction.channel.id, price.id, amount)
            button = button_class(self.platform, amount, price.unit_amount, url)
        else:
            button = button_class(self.platform)
        view = ui.View()
        view.add_item(button)
        view.add_item(CreditsDropdown(view, self.platform))
        await interaction.response.defer()
        await interaction.followup.edit_message(interaction.message.id, view=view)

        
class URLButton(discord.ui.Button):
    """Base class for URL buttons."""

    def __init__(self, platform: str, label: str, url: str, disabled: bool = False):
        self.platform = platform
        super().__init__(label=label, style=discord.ButtonStyle.url, url=url, disabled=disabled)


class VoteButton(URLButton):
    """Button for voting."""

    def __init__(self, platform: str, disabled: bool = False):
        super().__init__(platform, VOTE_CREDITS_LABEL.format(VOTE_CREDITS_AMOUNT), f"https://top.gg/bot/1080638505023193139/vote?a={platform.id}", disabled=disabled)


class ClaimButton(URLButton):
    """Button for claiming credits."""

    def __init__(self, platform: str):
        super().__init__(platform, CLAIM_CREDITS_LABEL.format(CLAIM_CREDITS_AMOUNT), DISCORD_INVITE)


class CreditsButton(URLButton):
    """Button for buying credits."""

    def __init__(self, platform: str, amount: int, price: int, url: str):
        super().__init__(platform, BUY_CREDITS_LABEL.format(amount, price / 100), url)


class HelpView(discord.ui.View):
    """View for displaying help options."""

    def __init__(self, page=None):
        super().__init__()
        if page:
            self.add_item(page)
        self.add_item(InviteButton())
        self.add_item(DiscordButton())
        self.add_item(HelpDropdown(self))


class DiscordButton(URLButton):
    """Button for joining the community server."""

    def __init__(self):
        super().__init__(label="Join the community server", url=DISCORD_INVITE)


class InviteButton(URLButton):
    """Button for adding the bot to a server."""

    def __init__(self):
        super().__init__(label="Add Dis.AI to your server", url=BOT_INVITE)
        

class HelpView(discord.ui.View):
    """A view for the help section."""
    def __init__(self, page=None):
        super().__init__()
        if page:
            self.add_item(page)
        self.add_item(InviteButton())
        self.add_item(DiscordButton())
        self.add_item(HelpDropdown(self))

class DiscordButton(ui.Button):
    """A button to join the community server."""
    def __init__(self):
        super().__init__(label="Join the community server", style=discord.ButtonStyle.url, url=DISCORD_INVITE)

class InviteButton(ui.Button):
    """A button to add the bot to your server."""
    def __init__(self):
        super().__init__(label="Add Dis.AI to your server", style=discord.ButtonStyle.url, url=BOT_INVITE)

class HelpDropdown(ui.Select):
    """A dropdown to select a help section."""
    def __init__(self, view):
        options = [discord.SelectOption(label="Overview", emoji="🌟"),
                   discord.SelectOption(label="Commands", emoji="🔮"),
                   discord.SelectOption(label="Chatbot settings", emoji="🖌️")]
        super().__init__(placeholder="👉   Select a help section  👈", options=options, min_values=1, max_values=1)
        self.original_view = view

    async def callback(self, interaction: discord.Interaction):
        try:
            if self.values[0] == "Overview":
                await interaction.response.edit_message(embed=help_overview_embed, view=HelpView(page=None))
            elif self.values[0] == "Commands":
                await interaction.response.edit_message(embed=chatbot_settings_embed, view=HelpView(page=RightHelpButtonSettings(self.original_view)))
            elif self.values[0] == "Chatbot settings":
                await interaction.response.edit_message(embed=commands_help_embed, view=HelpView(page=RightHelpButtonCommands(self.original_view)))
        except Exception as e:
            logging.error(e)



class HelpButton(ui.Button):
    """A button to navigate between help pages."""
    def __init__(self, label: str, view):
        super().__init__(label=label, style=discord.ButtonStyle.green)
        self.original_view = view

    async def update_view(self, interaction: discord.Interaction, embed, button):
        self.original_view.clear_items()
        self.original_view.add_item(button(self.original_view))
        self.original_view.add_item(InviteButton())
        self.original_view.add_item(DiscordButton())
        self.original_view.add_item(HelpDropdown(self.original_view))
        await interaction.response.defer()
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self.original_view)

class RightHelpButtonCommands(HelpButton):
    """A button to navigate to the next page of the commands help section."""
    def __init__(self, view):
        super().__init__(label="Page 2 ->", view=view)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.update_view(interaction, commands_help2_embed, LeftHelpButtonCommands)
        except Exception as e:
            logging.error(e)

class LeftHelpButtonCommands(HelpButton):
    """A button to navigate to the previous page of the commands help section."""
    def __init__(self, view):
        super().__init__(label="<- Page 1", view=view)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.update_view(interaction, commands_help_embed, RightHelpButtonCommands)
        except Exception as e:
            logging.error(e)

class SettingsButton(ui.Button):
    """A button to navigate between settings pages."""
    def __init__(self, label: str, view):
        super().__init__(label=label, style=discord.ButtonStyle.green)
        self.original_view = view

    async def update_view(self, interaction: discord.Interaction, embed, button):
        self.original_view.clear_items()
        self.original_view.add_item(button(self.original_view))
        self.original_view.add_item(InviteButton())
        self.original_view.add_item(DiscordButton())
        self.original_view.add_item(HelpDropdown(self.original_view))
        await interaction.response.defer()
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self.original_view)

class RightHelpButtonSettings(SettingsButton):
    """A button to navigate to the next page of the settings help section."""
    def __init__(self, view):
        super().__init__(label="Page 2 ->", view=view)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.update_view(interaction, chatbot_settings2_embed, LeftHelpButtonSettings)
        except Exception as e:
            logging.error(e)

class LeftHelpButtonSettings(SettingsButton):
    """A button to navigate to the previous page of the settings help section."""
    def __init__(self, view):
        super().__init__(label="<- Page 1", view=view)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.update_view(interaction, chatbot_settings_embed, RightHelpButtonSettings)
        except Exception as e:
            logging.error(e)


class BackToSelectionView(ui.View):
    """A view to go back to the selection."""
    def __init__(self, chatbot, platform):
        super().__init__()
        self.platform = platform
        self.add_item(BackToSelectionButton(chatbot, platform))

class BackToSelectionButton(ui.Button):
    """A button to go back to the settings."""
    def __init__(self, chatbot, platform):
        super().__init__(label="Back to settings", style=discord.ButtonStyle.grey, row=2)
        self.chatbot = chatbot
        self.platform = platform

    async def callback(self, interaction: discord.Interaction):
        view = discord.ui.View()
        view.add_item(SettingsListDropdown(self.platform, self.chatbot))
        view.add_item(RightSettingsButton(self.platform, self.chatbot))
        view.add_item(BackToChatbotSelectionButton(self.platform))
        embed = get_chatbot_settings_embed(self.chatbot.name, 1)
        await interaction.response.edit_message(embed=embed, view=view)

        
class PromptView(ui.View):
    """A view for prompting user actions."""

    def __init__(self, platform, chatbot, createcb_mode=False):
        super().__init__()
        try:
            backview = BackToPromptSelectionView(chatbot, platform, createcb_mode)
            promptdropdown = PromptDropdown(platform)
            promptsetbutton = PromptSetButton(platform, chatbot, promptdropdown, backview, createcb_mode)
            promptaddbutton = PromptAddButton(platform, backview)

            self.add_item(promptdropdown)
            self.add_item(promptsetbutton)
            self.add_item(promptaddbutton)

            if not createcb_mode:
                prompteditbutton = PromptEditButton(platform, chatbot, promptdropdown, backview)
                promptdeletebutton = PromptDeleteButton(platform, promptdropdown, backview)
                self.add_item(prompteditbutton)
                self.add_item(promptdeletebutton)
                self.add_item(BackToSelectionButton(chatbot, platform))
            else:
                promptavernbutton = PromptTavernButton(platform, chatbot)
                self.add_item(promptavernbutton)

            self.add_item(ui.Button(label="Dis.AI Community Server (browse community-made prompts)",
                                 url=DISCORD_INVITE, style=discord.ButtonStyle.url, row=2))

        except Exception as e:
            logger.error(f"Prompt view error: {e}")


class PromptDropdown(ui.Select):
    """A dropdown for selecting a prompt."""

    def __init__(self, platform):
        options = [discord.SelectOption(label=promptname) for promptname in platform.prompts.keys()]
        super().__init__(placeholder="Select Prompt  👈", options=options, min_values=1, max_values=1)
        self.platform = platform
        self.promptname = ""

    async def callback(self, interaction: Interaction):
        try:
            self.promptname = self.values[0]
            await interaction.response.defer()
        except Exception as e:
            logger.error(f"Prompt dropdown error: {e}")


class PromptSetButton(ui.Button):
    """A button for setting a prompt."""

    def __init__(self, platform, chatbot, promptdropdown, backview, createcb_mode=False):
        super().__init__(label="Assign prompt to chatbot", style=discord.ButtonStyle.green)
        self.chatbot = chatbot
        self.promptdropdown = promptdropdown
        self.platform = platform
        self.backview = backview
        self.createcb_mode = createcb_mode

    async def callback(self, interaction: Interaction):
        try:
            if self.promptdropdown.promptname:
                self.chatbot.prompt = str(self.platform.prompts[self.promptdropdown.promptname])
                self.chatbot.context.clear()
                await self.handle_namespace_deletion()
                await self.handle_prompt_assignment(interaction)
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"PromptSetButton error: {e}")

    async def handle_namespace_deletion(self):
        try:
            await delete_namespace(f"{self.platform.id}-{self.chatbot.name}")
        except Exception as e:
            logger.error(e)

    async def handle_prompt_assignment(self, interaction):
        if not self.createcb_mode:
            embed = discord.Embed(title=f"Successfully set prompt for {self.chatbot.name}", color=Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.backview)
            self.update_avatar_url()
        else:
            await self.handle_chatbot_creation(interaction)

    def update_avatar_url(self):
        for i in range(len(newprompts_avatars)):
            if self.promptdropdown.promptname == newprompts_avatars[i][0]:
                self.chatbot.avatar_url = newprompts_avatars[i][1]
                break

    async def handle_chatbot_creation(self, interaction):
        await dbhandler.add_cb_to_db(self.platform.id, await dbhandler.make_bot_dict(self.chatbot))
        self.platform.chatbots.append(self.chatbot)
        self.chatbot.context.clear()
        self.chatbot.prompt = str(self.platform.prompts[self.promptdropdown.promptname])
        embed = discord.Embed(title=f"🌟  Chatbot created: {self.chatbot.name}",
                      description=f"```/enable {self.chatbot.name}``` to **enable the chatbot** in the current channel\n\n"
                                  f"```/settings``` to **change the settings** (prompt, avatar, and much more)\n\n"
                                  f"```/help``` for help and more commands", colour=Colour.blue())
        self.platform.current_cb = None
        self.platform.waiting_for = ""
        view = make_inviteview()
        await interaction.response.edit_message(embed=embed, view=view)
        if self.chatbot.avatar_url == ICON_URL:
            self.update_avatar_url()
            
class BaseButton(ui.Button):
    """Base class for buttons with backviews. Backviews are views that are returned to after the button is pressed."""

    def __init__(self, platform, backview, label, style=discord.ButtonStyle.blurple):
        super().__init__(label=label, style=style)
        self.platform = platform
        self.backview = backview

    async def callback(self, interaction: Interaction):
        """Base callback method to be overridden by subclasses."""
        pass

class PromptAddButton(BaseButton):
    """Button for adding a new prompt."""
    def __init__(self, platform, backview):
        super().__init__(platform=platform, backview=backview, label="Add your own prompt")
        self.platform = platform
        self.backview = backview
        
    async def callback(self, interaction: Interaction):
        try:
            if len(self.platform.prompts) > MAX_PROMPTS:
                await send_error_message("You have too many prompts! Delete some before creating more.", interaction, view=self.backview)
                return
            await interaction.response.send_modal(PromptModal(self.platform, self.backview))
        except Exception as e:
            logger.error(f"PromptAddButton err: {e}")

class PromptTavernButton(BaseButton):
    """Button for Tavern Character Card."""

    def __init__(self, platform, chatbot):
        super().__init__(platform=platform, backview=None, label="Tavern Character Card")
        self.chatbot = chatbot

    async def callback(self, interaction: Interaction):
        try:
            view = ui.View()
            view.add_item(ui.Button(label="Dis.AI Community Server (browse community-made prompts)", url=DISCORD_INVITE, style=discord.ButtonStyle.url, row=1))
            embed = discord.Embed(title="Tavern Character Card: Attach or link the Tavern Character Card file below.", 
                          description="Make sure your chatbot name is exactly the same as the character's name!\n\nDon't know what this is? Join the community server!", 
                          color=Colour.blue())
            self.platform.waiting_for = "Tavern"
            self.platform.current_cb = self.chatbot
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"PromptTavernButton err: {e}")

class PromptJailbreakButton(BaseButton):
    """Button for adding jailbreak to Tavern chatbot."""

    def __init__(self, platform, chatbot):
        super().__init__(platform=platform, backview=None, label="Click to add jailbreak")
        self.chatbot = chatbot

    async def callback(self, interaction: Interaction):
        try:
            embed = discord.Embed(title=f"🌟  Tavern Chatbot created: {self.platform.name}", 
                          description=f"```/enable {self.chatbot.name}``` to **enable the chatbot** in the current channel\n\n```/settings``` to **change the settings** (prompt, avatar, and much more)\n\n```/help``` for help and more commands\n\nJailbreak added to prompt!", 
                          colour=Colour.blue())
            view = make_inviteview()
            prompt_jailbreak = jailbreak.replace("{{user}}", interaction.user.display_name).replace("{{char}}", self.chatbot.name)
            self.chatbot.prompt = prompt_jailbreak + self.chatbot.prompt
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"PromptJailbreakButton err: {e}")

class PromptEditButton(BaseButton):
    """Button for editing a prompt."""

    def __init__(self, platform, chatbot, promptdropdown, backview):
        super().__init__(platform=platform, backview=backview, label="Edit prompt")
        self.chatbot = chatbot
        self.promptdropdown = promptdropdown

    async def callback(self, interaction: Interaction):
        try:
            if self.promptdropdown.promptname:
                await interaction.response.send_modal(PromptEditModal(self.platform, self.promptdropdown.promptname, self.backview))
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"PromptEditButton err: {e}")

class BaseModal(ui.Modal):
    """Base class for modals with backviews."""

    def __init__(self, platform, backview, title):
        super().__init__(title=title)
        self.platform = platform
        self.backview = backview

    async def on_submit(self, interaction: Interaction):
        """Base submit method to be overridden by subclasses."""
        pass

class PromptEditModal(BaseModal):
    """Modal for editing a prompt."""

    def __init__(self, platform, promptname, backview):
        super().__init__(platform=platform, backview=backview, title="Edit Prompt")
        self.promptname = promptname

    response = ui.TextInput(label="Prompt", style=discord.TextStyle.long, placeholder="Act as a snarky, witty, short-tempered AI named Jarvis. Only respond how Jarvis would.")

    async def on_submit(self, interaction: Interaction):
        try:
            self.platform.prompts[self.promptname] = self.response.value
            embed = discord.Embed(title=f"Successfully edited prompt '{self.promptname}'\n\n**Important: Be sure to assign this prompt to your chatbot in order for the changes to take effect!**", color=Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.backview)
        except Exception as e:
            logger.error(f"PromptEditModal err: {e}")


class PromptModal(BaseModal):
    """Modal for entering a new prompt."""
    def __init__(self, platform, backview):
        super().__init__(platform=platform, backview=backview, title="Enter New Prompt")
    promptname = ui.TextInput(label="Name", style=discord.TextStyle.short, placeholder="Enter a name for the prompt")
    response = ui.TextInput(label="Prompt", style=discord.TextStyle.long, placeholder="Act as a snarky, witty, short-tempered AI named Jarvis. Only respond how Jarvis would.")

    async def on_submit(self, interaction: Interaction):
        try:
            if len(self.promptname.value) >= MAX_PROMPT_NAME_LENGTH:
                await send_error_message("Prompt name is too long! Choose a shorter name and try again.", interaction, view=self.backview)
                return
            self.platform.prompts[self.promptname.value] = str(self.response.value)
            embed = discord.Embed(title=f"Successfully added prompt '{self.promptname.value}' to your prompt library\n\n**Important: Be sure to go back and assign this prompt to your chatbot!", color=Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.backview)
        except Exception as e:
            logger.error(f"PromptModal err: {e}")
        
class PromptEditButton(ui.Button):
    """Button for editing a prompt."""

    def __init__(self, platform, chatbot, promptdropdown, backview):
        super().__init__(label="Edit prompt", style=discord.ButtonStyle.blurple)
        self.chatbot = chatbot
        self.promptdropdown = promptdropdown
        self.platform = platform
        self.backview = backview

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            if self.promptdropdown.promptname:
                await interaction.response.send_modal(PromptEditModal(self.platform, self.promptdropdown.promptname, self.backview))
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"PromptEditButton error: {e}")

class PromptEditModal(ui.Modal):
    """Modal for editing a prompt."""

    def __init__(self, platform, promptname, backview):
        super().__init__(title="Edit Prompt")
        self.platform = platform
        self.backview=backview
        self.promptname = promptname

    response = ui.TextInput(label="Prompt", style=discord.TextStyle.long, placeholder="Act as a snarky, witty, short-tempered AI named Jarvis. Only respond how Jarvis would.")

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        try:
            self.platform.prompts[self.promptname] = self.response.value
            embed = discord.Embed(title=f"Successfully edited prompt '{self.promptname}'", color=discord.Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.backview)
        except Exception as e:
            logger.error(f"PromptEditModal error: {e}")

class PromptDeleteButton(ui.Button):
    """Button for deleting a prompt."""

    def __init__(self, platform, promptdropdown, backview):
        super().__init__(label="Delete", style=discord.ButtonStyle.red)
        self.promptdropdown = promptdropdown
        self.platform = platform
        self.backview = backview

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            if len(self.platform.prompts) <= 1:
                await send_error_message("You cannot delete this prompt since you only have 1 prompt in your prompt library. Create more prompts to delete this one.", interaction, view=self.backview)
                return
            if self.promptdropdown.promptname:
                del self.platform.prompts[self.promptdropdown.promptname]
                embed = discord.Embed(title=f"Successfully deleted prompt '{self.promptdropdown.promptname}'", color=discord.Colour.blue())
                await interaction.response.edit_message(embed=embed, view=self.backview)
            else:
                await interaction.response.defer()
        except Exception as e:
            logger.error(f"PromptDeleteButton error: {e}")

class BackToPromptSelectionView(ui.View):
    """View for going back to prompt selection."""

    def __init__(self, chatbot, platform, createcb_mode=False):
        super().__init__()
        self.add_item(BackToPromptSelectionButton(chatbot, platform, createcb_mode))

class BackToPromptSelectionButton(ui.Button):
    """Button for going back to prompt selection."""

    def __init__(self, chatbot, platform, createcb_mode=False):
        super().__init__(label="Back to prompt selection", style=discord.ButtonStyle.grey)
        self.chatbot = chatbot
        self.platform = platform
        self.createcb_mode = createcb_mode

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            view = PromptView(self.platform, self.chatbot, self.createcb_mode)
            embed=get_prompt_library_embed(self.chatbot.name)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"BackToPromptSelectionButton error: {e}")

class EditAvatarModal(ui.Modal):
    """Modal for editing avatar."""

    def __init__(self, chatbot, backview):
        super().__init__(title="Enter Avatar URL")
        self.chatbot = chatbot
        self.backview = backview

    avatar_url = ui.TextInput(label="Avatar URL", placeholder="Chatbot will respond with this avatar")

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        try:
            self.chatbot.avatar_url = self.avatar_url.value.strip()
            embed=discord.Embed(title=f"Changed Avatar for {self.chatbot.name}", description="Note: If the avatar doesn't show properly, make sure you have entered a link to a valid image file. (The link should in in .png, .jpeg, etc.)", color=discord.Colour.blue())
            await interaction.response.edit_message(embed=embed, view=self.backview)
        except Exception as e:
            logger.error(f"EditAvatarModal error: {e}")

class LorebookView(ui.View):
    """A view for selecting lorebooks."""

    def __init__(self, platform, chatbot):
        super().__init__()
        try:
            lorebook_backview = BackToLorebookSelectionView(chatbot, platform)
            self.add_item(LorebookSetButton(platform, chatbot, lorebook_backview))
            if len(chatbot.lorebooks) > 0:
                self.add_item(LorebookDeleteButton(platform, chatbot, lorebook_backview))
            self.add_item(BackToSelectionButton(chatbot, platform))
            self.add_item(ui.Button(label="Dis.AI Community Server",
                                 url=DISCORD_INVITE, style=discord.ButtonStyle.url, row=2))

        except Exception as e:
            logger.error(f"Prompt view error: {e}")
            
class BackToLorebookSelectionView(ui.View):
    """View for going back to lorebook selection."""

    def __init__(self, chatbot, platform):
        super().__init__()
        self.add_item(BackToLorebookButton(chatbot, platform))

class BackToLorebookButton(ui.Button):
    """Button for going back to lorebook selection."""

    def __init__(self, chatbot, platform):
        super().__init__(label="Back to lorebook settings", style=discord.ButtonStyle.grey)
        self.chatbot = chatbot
        self.platform = platform

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            lorebook_str = '\n'.join(self.chatbot.lorebooks)
            if self.chatbot.lorebooks:
                desc_str = f"Current lorebooks:\n{lorebook_str}"
            else:
                desc_str = "No lorebooks have been added yet. Add one below!"
            await interaction.response.edit_message(embed=discord.Embed(title=f"{self.chatbot.name}'s lorebooks", description=desc_str, color = discord.Colour.blue()), view=LorebookView(self.platform, self.chatbot))
        except Exception as e:
            logger.error(f"BackToLorebookButton error: {e}")


class LorebookSetButton(ui.Button):
    """A button for assigning a lorebook to a chatbot."""

    def __init__(self, platform, chatbot, backview):
        super().__init__(label="Add new lorebook", style=discord.ButtonStyle.green)
        self.chatbot = chatbot
        self.platform = platform
        self.backview = backview

    async def handle_lorebook_assignment(self, interaction):
        if len(self.chatbot.lorebooks) >= 5:
            await send_error_message(interaction, "You can only assign up to 5 lorebooks to a chatbot. Please delete a lorebook and try again.", view=self.backview)
            return
        
        await interaction.response.send_modal(LorebookSetModal(self.platform, self.chatbot, self.backview))
        
    async def callback(self, interaction: Interaction):
        try:
            await self.handle_lorebook_assignment(interaction)
        except Exception as e:
            logger.error(f"LorebookSetButton error: {e}")
            
class LorebookSetModal(ui.Modal):
    """Modal for entering name for lorebook."""
    def __init__(self, platform, chatbot, backview):
        super().__init__(title="Enter lorebook name")
        self.platform = platform
        self.backview = backview
        self.chatbot = chatbot

    lorebook_name = ui.TextInput(label="Name", style=discord.TextStyle.short, placeholder="Lisa's Lorebook")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.platform.waiting_for = f"lorebook:{self.lorebook_name.value.strip()}"
            self.platform.current_cb = self.chatbot
            if self.lorebook_name.value in self.chatbot.lorebooks:
                await send_error_message(interaction, "A lorebook with this name already exists. Please choose a different name or delete the lorebook with this name.", view=self.backview)
                return
            embed=discord.Embed(title="Lorebooks: Attach lorebook below", description="You have a few options:\n1. Upload a rentry.org link\n2. Upload a .txt file containing the lorebook text", color=discord.Colour.blue())
            await interaction.response.edit_message(embed=embed, view=None)
        except ValueError as error:
            logger.error(f"lorebooksetmodal error: {error}")
            
class LorebookDeleteButton(ui.Button):
    """Button for deleting a lorebook."""

    def __init__(self, platform, chatbot, backview):
        super().__init__(label="Delete lorebook", style=discord.ButtonStyle.red)
        self.platform = platform
        self.chatbot = chatbot
        self.backview = backview

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            await interaction.response.send_modal(LorebookDeleteModal(self.platform, self.chatbot, self.backview))
        except Exception as e:
            logger.error(f"PromptDeleteButton error: {e}")
            
class LorebookDeleteModal(ui.Modal):
    """Modal for entering name for lorebook."""
    def __init__(self, platform, chatbot, backview):
        super().__init__(title="Enter lorebook name")
        self.platform = platform
        self.backview = backview
        self.chatbot = chatbot

    lorebook_name = ui.TextInput(label="Name", style=discord.TextStyle.short, placeholder="Lisa's Lorebook")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.lorebook_name.value in self.chatbot.lorebooks:
                self.chatbot.lorebooks.remove(self.lorebook_name.value)
                await delete_namespace(f"{self.platform.id}-{self.chatbot.name}-{self.lorebook_name.value}")
                embed = discord.Embed(title=f"Successfully deleted lorebook '{self.lorebook_name.value}'", color=discord.Colour.blue())
                await interaction.response.edit_message(embed=embed, view=self.backview)
            else:
                await send_error_message("A lorebook with this name does not exist. Please choose a different name.", interaction, view=self.backview)
        except ValueError as error:
            logger.error(f"LorebookDeleteModal error: {error}")