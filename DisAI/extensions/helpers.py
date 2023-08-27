import logging
from datetime import datetime, timedelta

import discord

from config import (
    CLAIM_CREDITS_AMOUNT,
    DISCORD_INVITE,
    GPT35_RESPONSE_COST,
    GPT4_RESPONSE_COST,
    ICON_URL,
    TIMEOUT_TIME,
    VOTE_CREDITS_AMOUNT,
    SUPPORT_SERVER_ID
)
from core.ChatBot import get_tokens
from extensions.constants import Analytics
from extensions.embeds import claim_embed
from utils.dbhandler import load_platform_to_memory

logger = logging.getLogger(__name__)

"""This file contains helper functions that are used in multiple places in the codebase."""

def get_platform_id(interaction: discord.Interaction) -> int:
    if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
        return interaction.guild.id
    return interaction.channel.id

def make_inviteview():
    invite_view = discord.ui.View()
    invite_view.add_item(discord.ui.Button(label="Dis.AI Community Server", url=DISCORD_INVITE, style=discord.ButtonStyle.url) )
    return invite_view

class VoteButton(discord.ui.Button):
    def __init__(self, platform, disabled=False):
        self.platform = platform
        super().__init__(label=f"Vote 🪙 x{VOTE_CREDITS_AMOUNT}  (Free)", style=discord.ButtonStyle.url, url=f"https://top.gg/bot/1080638505023193139/vote?a={platform.id}", disabled=disabled)
        
class ClaimButton(discord.ui.Button):
    def __init__(self, platform):
        self.platform = platform
        super().__init__(label=f"Claim 🪙 x{CLAIM_CREDITS_AMOUNT}  (Free)", style=discord.ButtonStyle.url, url=DISCORD_INVITE)
        
async def send_error_message(description, interaction, send_invite=True, view=None):
    embed=discord.Embed(title="Oops! Something went wrong", description=description, color=discord.Colour.red())
    if send_invite:
        view = make_inviteview() 
    if isinstance(interaction, discord.Interaction):
        await interaction.response.send_message(content=None, embed=embed, view=view, delete_after=TIMEOUT_TIME)
    elif isinstance(interaction, discord.Message):
        await interaction.channel.send(content=None, embed=embed, view=view, delete_after=TIMEOUT_TIME)
    elif isinstance(interaction, discord.TextChannel) or isinstance(interaction, discord.DMChannel):
        await interaction.send(content=None, embed=embed, view=view, delete_after=TIMEOUT_TIME)


async def update_analytics(analytics, stat):
    analytics.append((stat, datetime.now()))

async def get_platform(bot_platforms, interaction, stat=-1, id = None):
    platform = None
    try:
        if not id and interaction:
            id = get_platform_id(interaction)
        if id in bot_platforms:
            platform = bot_platforms[id]
            if stat != -1:
                await update_analytics(platform.analytics, stat)
        elif id not in bot_platforms:
            platform = await load_platform_to_memory(id, bot_platforms)
            
    except Exception as e:
        print(f"get platform err: {e}")
    return platform
    
def has_time_passed(datetime_obj, time_amount):
    current_datetime = datetime.now()
    target_datetime = datetime_obj + timedelta(seconds=time_amount)
    
    return current_datetime >= target_datetime

def get_credits_cost(model_name, messages=None):
    if model_name.endswith("4-0613"):
        return GPT4_RESPONSE_COST
    elif model_name == "gpt-3.5-turbo-16k":
        tokens_in_context = get_tokens("gpt-3.5-turbo", messages)
        if tokens_in_context > 2000:
            num_tokens += (tokens_in_context - 4000) // 1000
        return GPT35_RESPONSE_COST + num_tokens
    else:
        return GPT35_RESPONSE_COST

def get_chatbot_settings_embed(cb_name, page):
    return discord.Embed(title=f"🎨  Chatbot Settings (Page {page}/2)", description=f'**Selected chatbot: {cb_name}**\n`/help` for details about each setting', color=discord.Colour.blue())

def get_prompt_library_embed(cb_name):
    embed = discord.Embed(title="📚  Prompt Library  📚", description=f"Prompts make the magic happen  ✨\nUse prompts to customize your chatbot's personality, instructions, and behavior.\n\n**Select a prompt** to edit, delete, or assign to your chatbot\nOr, add your own prompt.\n\n**Selected chatbot: {cb_name}**\nUse the dropdown and choose a button to start.", color=discord.Colour.blue())
    embed.set_footer(text="Join the community server for tons of amazing prompts!")
    return embed

async def has_correct_perms(platform, interaction):
    if not platform.adminroles or any(role.id in platform.adminroles for role in interaction.user.roles) or interaction.user.guild_permissions.administrator:
        return True
    else:
        await send_error_message("You do not have permissions to use this command\n`/adminroles`", interaction, True)
        return False

async def claim_credits(interaction, platforms, to_delete=None):
    """Adds credits to the user's account in all mutual servers."""
    try:
        if not interaction.guild or (interaction.guild and interaction.guild.id != SUPPORT_SERVER_ID): # you can only claim in the support server.
            platform = await get_platform(platforms, interaction)
            view = discord.ui.View()
            view.add_item(VoteButton(platform))
            view.add_item(ClaimButton(platform))
            await interaction.response.send_message(embed=claim_embed, view=view, ephemeral=True)
        elif interaction.guild.id == SUPPORT_SERVER_ID:
            if isinstance(interaction, discord.Interaction):
                user = interaction.user
            else:
                user = interaction.author
            mutuals = user.mutual_guilds
            id = user.id
            added_credits = [] 
            already_claimed = []
            for guild in mutuals:
                if guild.id != 1088158471167410308:
                    try:
                        platform = await get_platform(platforms, interaction, Analytics.CLAIMCOMMAND.value, id=guild.id)
                        if str(id) in platform.claimers:
                            if has_time_passed(platform.claimers[str(id)], 43200):
                                platform.credits += CLAIM_CREDITS_AMOUNT
                                added_credits.append(guild.name)
                                platform.claimers[str(id)] = datetime.now()
                            else:
                                already_claimed.append(guild.name)
                        else:
                            platform.claimers[str(id)] = datetime.now()
                            platform.credits += CLAIM_CREDITS_AMOUNT
                            added_credits.append(guild.name)
                    except Exception as e:
                        print(f"inner /claim err: {e}")
            try:
                if user.dm_channel:
                    platform = await get_platform(platforms, interaction, Analytics.CLAIMCOMMAND.value, id=interaction.user.dm_channel.id)
                    if platform:
                        if str(id) in platform.claimers:
                            if has_time_passed(platform.claimers[str(id)], 43200):
                                platform.credits += CLAIM_CREDITS_AMOUNT
                                platform.claimers[str(id)] = datetime.now()
                                added_credits.append(f"DM Channel with {interaction.user.display_name}") # old, DM channels no longer supported
                            else:
                                already_claimed.append(f"DM Channel with {interaction.user.display_name}")
                        else:
                            platform.claimers[str(id)] = datetime.now()
                            platform.credits += CLAIM_CREDITS_AMOUNT
                            added_credits.append(f"DM Channel with {interaction.user.display_name}")
            except Exception as e:
                print(f"/claim user part err: {e}")

            if added_credits:
                joined = '\n'.join(added_credits)
                out = f"**Added 🪙 x{CLAIM_CREDITS_AMOUNT} credits to the following:**\n{joined}"
            else: 
                out = ""
            if already_claimed:
                joined = '\n'.join(already_claimed)
                out2 = f"**You've already claimed credits for the following in the past 12h:**\n{joined}"
            else:
                out2 = ""
            embed=discord.Embed(title="🪙  Credits Claimed", description=f"{out}\n\n{out2}", color=discord.Colour.blue())
            embed.set_thumbnail(url=ICON_URL)
            if isinstance(interaction, discord.Interaction):
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.author.send(embed=embed)
                await to_delete.delete()
    except Exception as e:
        print(f"Claim func err: {type(e)} {e}")