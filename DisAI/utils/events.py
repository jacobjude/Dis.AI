import os
import io
import re
import json
import base64
import asyncio
import requests
import urllib.parse
from time import perf_counter
from datetime import datetime
from math import ceil
from random import choice
from PIL import Image
from PIL.ExifTags import TAGS
import discord
import aiohttp
from bs4 import BeautifulSoup
import PyPDF2
import topgg
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Optional
from pathlib import Path
import logging

from utils import dbhandler
import utils.encrypt as encrypt
from utils.messagehandler import process_ai_response, handle_gpt_response
from utils.pineconehandler import upsert_data, delete_namespace
from extensions.uiactions import PromptJailbreakButton
from extensions.helpers import (
    send_error_message,
    has_time_passed,
    make_inviteview,
    get_platform,
    update_analytics,
    get_credits_cost,
    claim_credits,
)
from extensions.constants import Analytics
from core.ChatBot import default_chat_bot
from core.Server import Server
from config import (
    PDF_CHUNK_LENGTH,
    UPLOAD_DATA_COST,
    YOUTUBE_VIDEO_STRIDE,
    YOUTUBE_VIDEO_WINDOW,
    PDF_STRIDE,
    PDF_WINDOW,
    VOTE_CREDITS_AMOUNT,
    main_prompt,
    SUPPORT_SERVER_ID,
    STATUS_CHANNEL_ID,
    YOUTUBE_API_KEY,
    OWNER_ID,
    STRIPE_WEBHOOK_CHANNEL,
    VOTE_WEBHOOK_CHANNEL,
    DBL_TOKEN,
    DBL_PASSWORD,
)

youtube_pattern = re.compile(r'(?:https?://)?(?:www\.)?youtu(?:\.be/|be\.com/(?:watch\?(?:.*&)?v=|v/|embed/|user/[^/]+#p/(?:[^/]+/)+))([^/&?#]+)')

HOUR_IN_SECONDS = 3600
MINUTE_IN_SECONDS = 60
TEXT_CHUNK_SIZE = 12000
MAX_FILE_SIZE_MB = 20
MAX_PAGES = 1000

PNG_EXTENSION = ".png"
PDF_EXTENSION = ".pdf"
TXT_EXTENSION = ".txt"
PDF_CHUNK_LENGTH = 1000
PDF_WINDOW = 100
PDF_STRIDE = 100
YOUTUBE_VIDEO_WINDOW = 100
YOUTUBE_VIDEO_STRIDE = 100

OWNER_COMMAND_PREFIX = "ai."
LOREBOOK_WAITING = "lorebook"
TAVERN_WAITING = "Tavern"
LONG_PROMPT_WAITING = "Long Prompt"
DATA_WAITING = "data"
CLAIM_COMMAND = "/claim"

REGENERATE_EMOJI = '🔃'
CONTINUE_EMOJI = '⏩'
DELETE_EMOJI = '🗑️'
WEBHOOK_NAME = "Dis.AI Webhook"
logger = logging.getLogger(__name__)

async def convert_seconds_to_timestamp(seconds: int) -> str:
    """Convert seconds to timestamp format."""
    hours = seconds // HOUR_IN_SECONDS
    minutes = (seconds % HOUR_IN_SECONDS) // MINUTE_IN_SECONDS
    remaining_seconds = seconds % MINUTE_IN_SECONDS

    timestamp = "{:02d}:{:02d}:{:02d}".format(hours, minutes, remaining_seconds) if hours > 0 else "{:02d}:{:02d}".format(minutes, remaining_seconds)
    return timestamp


class SummarizeButton(discord.ui.Button):
    """Button to summarize texts after uploading PDF/YouTube videos."""

    def __init__(self, platform, chatbot, user_message, texts, data_name):
        self.texts = texts
        self.credits_cost = ceil(((len(self.texts) // TEXT_CHUNK_SIZE) + 1) * 1.5)
        super().__init__(label=f"Summarize (🪙x{self.credits_cost})", style=discord.ButtonStyle.blurple)
        self.platform = platform
        self.chatbot = chatbot
        self.user_message = user_message
        self.data_name = data_name

    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        try:
            await self.handle_summary(interaction)
        except Exception as error:
            logging.error(error)

    async def handle_summary(self, interaction: discord.Interaction):
        """Handle the summarization process. We create a new summary chatbot with the following settings."""
        summary_chatbot = await default_chat_bot("summary_chatbot")
        summary_chatbot.prompt = f"Write short, expert, bulletpoint summaries on the given excerpt from the {self.data_name}."
        summary_chatbot.temperature = 0
        summary_chatbot.presence_penalty = 0
        summary_chatbot.frequency_penalty = 0
        summary_chatbot.context.append({'role':'system', 'content':summary_chatbot.prompt})
        summary_chatbot.context.append({'role':'user', 'content':''})
        await interaction.response.edit_message(view=None, embed=discord.Embed(title=f"Summarizing {self.data_name}", colour=discord.Colour.blue()))
        for i in range(0, len(self.texts), TEXT_CHUNK_SIZE):
            summary_chatbot.context[1]['content'] = self.texts[i:i + TEXT_CHUNK_SIZE]
            await handle_gpt_response(self.platform, summary_chatbot, self.user_message, credits_cost=self.credits_cost, response_message=None, converse_mode=True, should_make_regen_button=False, should_make_continue_button=False)
            del summary_chatbot.context[-1]
        self.platform.credits -= self.credits_cost


def check_for_youtube_link(message_content: str) -> Optional[str]:
    """Check if the message contains a YouTube link."""
    match = youtube_pattern.search(message_content)
    return match.group(1) if match else None


async def get_video_title(video_id: str) -> str:
    """Get the title of a YouTube video."""
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if "items" in data and data["items"]:
                return data["items"][0]["snippet"]["title"]
            else:
                return ""


async def download_pdf(url: str, file_name: str) -> str:
    """Download a PDF and extract its text."""
    try:
        return await handle_pdf_download(url, file_name)
    except Exception as error:
        logging.error(f"dl pdf err: {error}")
        return ""


async def handle_pdf_download(url: str, file_name: str) -> str:
    """Handle the PDF download process."""
    text_w_pages = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                pdf_data = await response.read()  # Read response content as bytes
                file_path = Path(f"pdfs/{file_name}.txt")
                file_path.write_bytes(pdf_data)
                pdf_reader = PyPDF2.PdfReader(file_path.open('rb'))
                file_size = file_path.stat().st_size
                num_pages = len(pdf_reader.pages)
                if file_size / (1024 * 1024) > MAX_FILE_SIZE_MB or num_pages > MAX_PAGES:
                    return -1
                text = ''
                for page_num in range(num_pages):
                    await asyncio.sleep(0)  # so the bot can do other stuff
                    page = pdf_reader.pages[page_num]
                    text_w_pages[page_num] = page.extract_text().replace('\n', '')
                return text_w_pages



async def on_ready(bot):
    """
    This function is called when the bot is ready.
    """
    try:
        logger.info("Getting ready.")
        
        # change status, set up top.gg
        game = discord.Game("/create")
        await bot.change_presence(status=discord.Status.online, activity=game)
        bot.topggpy = topgg.DBLClient(bot, DBL_TOKEN)
        bot.topgg_webhook = topgg.WebhookManager(bot).dbl_webhook("/dblwebhook", DBL_PASSWORD)
        
        logger.info("Changed presence and enabled topgg webhook. getting key and adding guilds to db.")
        logger.info(encrypt.get_key())
        await dbhandler.add_guilds_to_db(bot) # add all guilds that the bot can see to database
        logger.info("Added guilds to database.")
        tic = perf_counter()
        await dbhandler.load_database_to_memory(bot)
        toc = perf_counter()
        logger.info(f"Loaded database to memory in {toc - tic:0.4f} seconds")
        try: # send a message to the status channel in the support server
            support_server = await bot.fetch_guild(SUPPORT_SERVER_ID)
            status_channel = await support_server.fetch_channel(STATUS_CHANNEL_ID)
            possible_emojis = ["<:DoNotBangTheMachines:1125270839504420904>", "<:amogus:1125271197261779036>","<a:gato:1125291480571985970>","<:Catt:1125270836828442674>","<a:alienpls3:1125271141355880460>"]
            emoji = choice(possible_emojis)
    
            await status_channel.send(f"🟢  Online!")
            await status_channel.send(emoji)
        except Exception as e:
            logger.error("Error sending online message: %s", e)
        logger.info("Load DB to memory. Now loading bingbots for each chatbot")
        logger.info("Loaded everything. Ready.")
    except Exception as e:
        logger.error(e)


async def on_guild_remove(bot, guild):
    """
    This function is called when the bot is removed from a guild. 
    This is just used for analytics purposes, to see how many guilds the bot has been removed from.
    """
    bot.left_guilds.append(guild.id)
        
async def on_message(bot, message):
    """Handles incoming messages."""
    try:
        if message.author.id == bot.user.id: # ignore messages from the bot
            return

        if message.author.id == OWNER_ID and message.content.startswith(OWNER_COMMAND_PREFIX): # owner commands
            await bot.process_commands(message)
            return
        elif message.content.startswith(CLAIM_COMMAND): # claim credits
            await claim_credits(bot, message)
            return

        # i have a webhook for stripe and top.gg that sends a message to a (private) channel on my support server on purchases / votes, so i need to handle those
        if message.channel.id == STRIPE_WEBHOOK_CHANNEL:
            await handle_stripe_webhook(bot, message)
            return
        elif message.channel.id == VOTE_WEBHOOK_CHANNEL:
            await handle_vote_webhook(bot, message)
            return
        
        if message.author.bot:
            return

        
        platform = await get_platform(bot.platforms, None, -1, message.guild.id) # get the platform for this guild
        if not has_time_passed(platform.last_interaction_date, 2): # effecitvely a 2 second cooldown
            return

        now = datetime.now()
        platform.last_interaction_date = now

        if platform.waiting_for:
            await handle_waiting_for(platform, message)
            return

        if message.content:
            await process_ai_response(platform, message, bot.user)

    except Exception as e:
        logger.error(f"on message err: {type(e)} - {e}")
        raise

async def handle_stripe_webhook(bot, message):
    """Handles Stripe webhooks."""
    logger.info("stripe hook received")
    hook_dict = json.loads(message.content.replace("'", "\"")) # webhook sends a dictionary as a string. extract its contents and add credits.
    platform = await get_platform(bot.platforms, None, -1, int(hook_dict["platform_id"]))
    noun_str = "this server" if isinstance(platform, Server) else "this DM Channel" # there used to be support for chatting in DM channels, but it was removed
    embed = create_payment_embed(hook_dict, noun_str)
    platform.credits += int(hook_dict["credits"])

    if isinstance(platform, Server):
        await bot.get_channel(hook_dict["channel_id"]).send(embed=embed)
    else:
        user = await bot.fetch_user(platform.user_id)
        await user.send(embed=embed)

async def handle_vote_webhook(bot, message):
    """Handles vote webhooks."""
    logger.info("vote received")
    platform_id = int(message.content[message.content.index('a') + 2:message.content.index(' ')])
    platform = await get_platform(bot.platforms, None, -1, platform_id)
    platform.credits += VOTE_CREDITS_AMOUNT

async def handle_waiting_for(platform, message):
    """Handles platform waiting for events."""
    handlers = {
        TAVERN_WAITING: handle_tavern_waiting_for,
        LONG_PROMPT_WAITING: handle_long_prompt_waiting_for,
        DATA_WAITING: handle_data_waiting_for,
    }
    if platform.waiting_for.startswith(LOREBOOK_WAITING): # lorebook waiting_for string is in the form "lorebook:lorebook_name" so we can't just use the dict
        handler = handle_lorebook_waiting_for
    else:
        handler = handlers.get(platform.waiting_for)
    if handler:
        await handler(platform, message)
    platform.current_cb = None
    platform.waiting_for = None

async def extract_text_from_url(url):
    """Extracts the raw text data from a url."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()  # Raise an exception if the request was not successful
                return await response.text()
    except aiohttp.ClientError as e:
        print(f"An error occurred: {e}")
        return None

async def handle_lorebook_waiting_for(platform, message):
    """Handles Lorebook waiting for events. Takes the rentry.org link and extracts the raw text data"""
    if message.content and 'rentry.org' in message.content:
        await handle_lorebook_rentry(platform, message)
    elif message.attachments and message.attachments[0].url.endswith(TXT_EXTENSION): # check for .txt attachment in message
        await handle_lorebook_txt(platform, message)
    else:
        await send_error_message("Invalid Rentry link. Try again from `/create` with a valid link", message)
        
async def handle_lorebook_rentry(platform, message):
    """Handles Lorebook rentry.org links."""
    try:
        url = message.content
        rentry_index = url.find('rentry.org')
        # first, make sure the url is in the form https://rentry.org/blahblahblah/raw
        if not url.startswith("https://"):
            url = url[rentry_index:]
            url = "https://" + url
        if not url.endswith("/raw") and url[-1] == '/': # add /raw if it's not there
            url = url + "raw"
        elif not url.endswith("/raw") and url[-1] != '/': # in case there's no '/' at the end   
            url = url + "/raw"
            
        text = await extract_text_from_url(url)
        lines = text.split('\n')
        chunked_text = [line for line in lines if line.strip() != ''] # get rid of empty lines
        lorebook_name = platform.waiting_for[platform.waiting_for.find(":") + 1:].strip() # get the lorebook name from the waiting_for string, which is in the form "lorebook:lorebook_name"
        embed = discord.Embed(title="Lorebook Creation", description=f"Creating lorebook: {lorebook_name}", color=discord.Color.blue())
        message_to_edit = await message.channel.send(embed=embed) 
        data = [{'role': 'entry', 'content': line} for line in chunked_text]
        await upsert_data(data, f"{platform.id}-{platform.current_cb.name}-{lorebook_name}", 0, 2, 2, batch_size=100, type="lorebook", message_to_edit=message_to_edit)
        platform.current_cb.lorebooks.append(lorebook_name)
        embed=discord.Embed(title=f"Lorebook: {lorebook_name}", description="Lorebook created!", color=discord.Color.blue())
        await message_to_edit.edit(embed=embed)
        
    except Exception as e:
        print(e)
        await send_error_message("Invalid Rentry link. Try again from `/settings` with a valid link", message)

async def handle_lorebook_txt(platform, message):
    try:
        text = await message.attachments[0].read()
        text = text.decode('utf-8')
        lines = text.split('\n')
        chunked_text = [line for line in lines if line.strip() != ''] # get rid of empty lines
        lorebook_name = platform.waiting_for[platform.waiting_for.find(":") + 1:].strip() # get the lorebook name from the waiting_for string, which is in the form "lorebook:lorebook_name"
        embed = discord.Embed(title="Lorebook Creation", description=f"Creating lorebook: {lorebook_name}", color=discord.Color.blue())
        message_to_edit = await message.channel.send(embed=embed) 
        data = [{'role': 'entry', 'content': line} for line in chunked_text]
        await upsert_data(data, f"{platform.id}-{platform.current_cb.name}-{lorebook_name}", 0, 2, 2, batch_size=100, type="lorebook", message_to_edit=message_to_edit)
        platform.current_cb.lorebooks.append(lorebook_name)
        embed=discord.Embed(title=f"Lorebook: {lorebook_name}", description="Lorebook created!", color=discord.Color.blue())
        await message_to_edit.edit(embed=embed)
    except Exception as e:
        print(e)
        await send_error_message("Invalid Rentry link. Try again from `/settings` with a valid link", message)
    
async def handle_tavern_waiting_for(platform, message):
    """Handles Tavern waiting for events."""
    if message.content.endswith(".png") or (message.attachments and message.attachments[0].url.endswith(".png")):
        await handle_tavern_png(platform, message)
    elif (message.attachments and message.attachments[0].url.endswith(".json")):
        await handle_tavern_json(platform, message)
    else:
        await send_error_message("Invalid TavernAI PNG file. Try again from `/create` with a valid file\nYou can also upload .json files.", message)


def replace_strings(prompt, platform, message):
    """Replace keywords in the prompt with the appropriate values. This is for TavernAI prompts."""
    replacements = {
        "{{char}}": platform.current_cb.name,
        "{{Char}}": platform.current_cb.name,
        "{{user}}": message.author.display_name,
        "{{User}}": message.author.display_name,
        "{{USER}}": message.author.display_name,
        "\\n": "\n",
        "\\r": "",
        "\\t": ""
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    return prompt

async def handle_tavern_png(platform, message):
    """Handles TavernAI PNG files."""
    try:
        link = message.content if message.content.endswith(PNG_EXTENSION) else message.attachments[0].url
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                # read the png file and get the prompt from the metadata
                png_file = await response.read()
                image = Image.open(io.BytesIO(png_file))
                exif_data = image.getexif()
                prompt = base64.b64decode(image.info['chara']).decode("utf-8", errors="ignore")
                
                # start formatting the prompt and create the chatbot
                prompt = replace_strings(prompt, platform, message)
                prompt += "\n\n<START>\n"
                prompt = main_prompt + prompt
                platform.current_cb.prompt = prompt
                platform.current_cb.context.clear()
                platform.current_cb.avatar_url = link
                await dbhandler.add_cb_to_db(platform.id, await dbhandler.make_bot_dict(platform.current_cb))
                platform.chatbots.append(platform.current_cb)
                platform.current_cb.context.clear()
                embed = create_tavern_chatbot_embed(platform.current_cb)
                view = make_inviteview()
                view.add_item(PromptJailbreakButton(platform, platform.current_cb))
                await message.channel.send(embed=embed, view=view)
    except Exception as e:
        logging.error(f"process png err: {e}")
        await send_error_message("Invalid TavernAI PNG file. Try again from `/create` with a valid file\nYou can also upload .json files.", message)
        logging.error(image.info)
    platform.waiting_for = "" # probably redundant, but just in case
    platform.current_cb = None

async def handle_tavern_json(platform, message):
    """Handles TavernAI JSON files."""
    try:
        prompt = await message.attachments[0].read()
        prompt = prompt.decode('utf-8')
        prompt = replace_strings(prompt, platform, message)
        prompt = prompt.strip()
        try:
            json.loads(prompt, strict=False)
        except Exception as e:
            logging.error(e)
        prompt += "\n<START>\n"
        platform.current_cb.prompt = prompt
        await dbhandler.add_cb_to_db(platform.id, await dbhandler.make_bot_dict(platform.current_cb))
        platform.chatbots.append(platform.current_cb)
        platform.current_cb.context.clear()
        embed = create_tavern_chatbot_embed(platform.current_cb)
        view = make_inviteview()
        await message.channel.send(embed=embed, view=view)
    except Exception as e:
        await send_error_message("Invalid TavernAI PNG file. Try again from `/create`\nYou can also upload .json files.", message)
    platform.waiting_for = ""  # probably redundant, but just in case
    platform.current_cb = None

async def handle_long_prompt_waiting_for(platform, message):
    """Handles long prompts. Allows users to bypass discord's character limit."""
    try:
        if message.attachments and message.attachments[0].url.endswith(TXT_EXTENSION): # check for .txt attachment in message
            prompt = await message.attachments[0].read()
            prompt = prompt.decode('utf-8')
            if len(prompt) > 6000:
                await send_error_message("Prompt is too long.", message)
                return
            prompt = str(prompt).replace('\r', '').replace('\n', '').replace('\\r', '').replace('\\n', '').replace('\\t', '').replace('\t', '')
            platform.current_cb.prompt = prompt[:4000]
            platform.current_cb.context.clear()
            promptname = f"(Long prompt) {prompt[:15]}..."
            platform.prompts[promptname] = prompt
            embed = discord.Embed(title=f"Set Prompt for {platform.current_cb.name}", description=f"Prompt name:\n{promptname}", color=discord.Colour.blue())
            await message.channel.send(embed=embed)
            try:
                await delete_namespace(f"{platform.id}-{platform.current_cb.name}")
                await delete_namespace(f"{platform.id}-{platform.current_cb.name}-data")
            except:
                pass
        else:
            await send_error_message(f"No {TXT_EXTENSION} file uploaded. Try again from /settings.", message)
    except Exception as e:
        await send_error_message(f"An error occurred. Try again from /settings.", message)
        logger.error(f"Long prompt err: {e}")
    platform.waiting_for = ""
    platform.current_cb = None

async def handle_data_waiting_for(platform, message):
    """Handle platform waiting_for event. (ie., user is uploading a tavern prompt, long prompt, YouTube/PDF, or lorebook)"""
    data = []
    texts = ""
    youtube_video_id = check_for_youtube_link(message.content)
    if youtube_video_id:
        embed_message = await message.channel.send(embed=create_processing_video_embed())
        try:
            transcript = YouTubeTranscriptApi.get_transcript(youtube_video_id)
            texts = [x['text'] for x in transcript] # transcript text
            for i in range(len(texts)):
                data.append({'location': await convert_seconds_to_timestamp(int(transcript[i]['start'])), 'content': texts[i]}) # data is a {'location', 'content'} dict
            try:
                await delete_namespace(f"{platform.id}-{platform.current_cb.name}-data") # delete any old data in pinecone.
            except:
                pass
            title = await get_video_title(youtube_video_id)
            platform.current_cb.data_name = f"YouTube Video - '{title[:120]}'"
            await upsert_data(data, f"{platform.id}-{platform.current_cb.name}-data", platform.current_cb.batch_number + 1, window=YOUTUBE_VIDEO_WINDOW, stride=YOUTUBE_VIDEO_STRIDE, batch_size=100, type="Video", message_to_edit=embed_message)
            await embed_message.edit(embed=create_video_stored_embed(platform.current_cb.data_name, platform))
            texts = ''.join(texts)
        except Exception as e:
            await send_error_message(f"Unexpected error. Please join the support server if this persists.\n{e}", message)
    elif (message.content.endswith(PDF_EXTENSION) or (message.attachments and message.attachments[0].url.endswith(PDF_EXTENSION))): # check if pdf uploaded. could be a url or direct upload
        try:
            embed_message = await message.channel.send(embed=create_processing_pdf_embed())
            url = message.content if message.content.endswith(PDF_EXTENSION) else message.attachments[0].url
            platform.current_cb.data_name = f"PDF - '{os.path.basename(urllib.parse.urlparse(url).path)[:40]}'"
            texts_w_pages = await download_pdf(url, f"{platform.id}-{platform.current_cb.name}")

            if texts_w_pages == -1:
                await send_error_message(f"PDFs must be fewer than 1000 pages and less than 25 MB.", message)
                platform.waiting_for = ""
                platform.current_cb = None
                return
            elif not texts_w_pages:
                await send_error_message(f"{platform.current_cb.data_name}' either contains no text or failed to process. \nTry again from `/settings`", message)
                platform.waiting_for = ""
                platform.current_cb = None
                return
            texts = ''.join(texts_w_pages.values())
            for page in texts_w_pages:
                for i in range(0, len(texts_w_pages[page]), PDF_CHUNK_LENGTH):
                    data.append({'location': page, 'content': texts_w_pages[page][i:i+PDF_CHUNK_LENGTH]})
            try:
                await delete_namespace(f"{platform.id}-{platform.current_cb.name}-data")
                await upsert_data(data, f"{platform.id}-{platform.current_cb.name}-data", platform.current_cb.batch_number + 1, window=PDF_WINDOW, stride=PDF_STRIDE, batch_size=100, type="PDF", message_to_edit=embed_message)
            except:
                pass

            await embed_message.edit(embed=create_pdf_stored_embed(platform.current_cb.data_name))

        except Exception as e:
            logging.error(f"pdf upload err: {e}")
            await send_error_message(f"Unexpected error. Please join the support server if this persists.\n{e}", message)
    else:
        await send_error_message(f"No PDF or YouTube video has been uploaded. Please try again from /settings.", message)
        platform.waiting_for = ""
        platform.current_cb = None


# Some helper functions

def create_payment_embed(hook_dict, noun_str):
    return discord.Embed(
        title="Payment successful",
        description=f"Credits (🪙 x{hook_dict['credits']}) have been automatically added to {noun_str}.\nThank you for your support, <@{hook_dict['user_id']}>. Enjoy! ❤️",
        color=discord.Colour.blue()
    )

def create_tavern_chatbot_embed(chatbot):
    return discord.Embed(
        title=f"🌟  Tavern Chatbot created: {chatbot.name}",
        description=f"```/enable {chatbot.name}``` to **enable the chatbot** in the current channel\n\n```/settings``` to **change the settings** (prompt, avatar, and much more)\n\n```/help``` for help and more commands",
        colour=discord.Colour.blue()
    )

def create_processing_video_embed():
    return discord.Embed(
        title="Processing video...",
        description="0% Processed\n\n(This may take a while for long videos...)",
        color=discord.Colour.blue()
    )

def create_video_stored_embed(data_name, platform):
    return discord.Embed(
        title=f"{data_name} has been stored in {platform.current_cb.name}'s long term memory",
        description=f"Any preexisting PDF or YouTube Video has been removed from memory.\nYou have 🪙 x{platform.credits} credits remaining.",
        color=discord.Colour.blue()
    )

def create_processing_pdf_embed():
    return discord.Embed(
        title="Processing PDF...",
        description="This may take a while for large files...",
        color=discord.Colour.blue()
    )

def create_pdf_stored_embed(data_name, platform):
    return discord.Embed(
        title=f"{data_name} has been stored in {platform.current_cb.name}'s long term memory",
        description=f"Any preexisting PDF or YouTube Video for this chatbot has been removed from memory.\nYou have 🪙 x{platform.credits} credits remaining.",
        color=discord.Colour.blue()
    )

async def on_raw_reaction_add(bot, payload):
    """Handles the event when a reaction is added to a message."""
    try:
        if payload.user_id == bot.user.id:
            return

        channel = await bot.fetch_channel(payload.channel_id)
        our_webhook = await get_webhook(channel, payload.guild_id)

        if our_webhook is None:
            return

        message = await channel.fetch_message(payload.message_id)
        user = message.author
        id = message.guild.id if message.guild else channel.id
        chatbot = await get_chatbot(our_webhook, user, id, bot.platforms)

        if chatbot is None:
            return

        platform = bot.platforms[id]

        if payload.emoji.name == REGENERATE_EMOJI:
            await handle_reaction(chatbot, message, platform, Analytics.REGENERATE.value, True)
        elif payload.emoji.name == CONTINUE_EMOJI:
            await handle_reaction(chatbot, message, platform, Analytics.CONTINUE.value, False)
        elif payload.emoji.name == DELETE_EMOJI:
            await handle_delete_reaction(chatbot)

    except Exception as e:
        logger.error(f"reaction err: {e}")

async def get_webhook(channel, guild_id):
    """Fetches the webhook for the given channel and guild."""
    if guild_id:
        webhooks = await channel.webhooks() if not isinstance(channel, discord.Thread) else await channel.parent.webhooks()
        for webhook in webhooks:
            if webhook.name == WEBHOOK_NAME:
                return webhook
    else:
        return None

async def get_chatbot(our_webhook, user, id, platforms):
    """Fetches the chatbot for the given webhook, user, and id."""
    if user.bot and user.id == our_webhook.id:
        platform = await get_platform(platforms, None, id=id)
        for chatbot in platform.chatbots:
            if isinstance(platform, Server) and chatbot.name == user.name:
                return chatbot
            elif chatbot.channels and chatbot.channels[0] == id:
                return chatbot

async def handle_reaction(our_chatbot, message, platform, action, regen_mode):
    """Handles a reaction event."""
    await update_analytics(platform.analytics, action)
    cost = get_credits_cost(our_chatbot.model)
    await message.clear_reactions()
    if regen_mode:
        del our_chatbot.context[-1]
    else:
        our_chatbot.context.append({'role':'system','content':'Continue'})
    response_success = await handle_gpt_response(platform, our_chatbot, user_message=message, credits_cost=cost, response_message=our_chatbot.last_message if regen_mode else None, should_append_context=False)
    if response_success:
        platform.credits -= cost

async def handle_delete_reaction(our_chatbot):
    """Handles a delete reaction event."""
    del our_chatbot.context[-2:]
    await our_chatbot.last_message.delete()
    our_chatbot.last_message = None
