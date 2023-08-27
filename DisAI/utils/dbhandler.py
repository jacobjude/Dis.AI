import pymongo
import json
import logging
from datetime import datetime, timedelta
from core.ChatBot import ChatBot
from core.Server import Server
import utils.encrypt as encrypt
from config import (MONGO_LINK, MONGO_NAME, PROMPT1NAME, PROMPT1VALUE, PROMPT2NAME, 
                    PROMPT2VALUE, PROMPT3NAME, PROMPT3VALUE, PROMPT4NAME, PROMPT4VALUE, 
                    PROMPT5NAME, PROMPT5VALUE, DEFAULTCREDITSAMOUNT)
import asyncio

# Constants
SECONDS_DELAY = 45

# Setup logging
logger = logging.getLogger(__name__)

mongoclient = pymongo.MongoClient(MONGO_LINK)
db = mongoclient[MONGO_NAME] # collection name

async def add_guilds_to_db(bot: ChatBot) -> None:
    """
    If a server joins while the bot is down, this function adds it to the database and to memory
    """
    for guild in bot.guilds:
        if not [gid for gid in db.platforms.find({"_id": guild.id})]:
            try:
                await add_guild_to_db(bot, guild)
            except Exception as e:
                logger.error(f"add guilds to db err: {e}")

async def add_guild_to_db(bot: ChatBot, guild: Server) -> None:
    """
    Add a guild to the database
    """
    try:
        new_server = Server(
            id=guild.id,
            name=guild.name,
            last_interaction_date=datetime.now().replace(microsecond=0),
            waiting_for="",
            current_cb="",
            voting_channel_id=0,
            adminroles=[], 
            credits=DEFAULTCREDITSAMOUNT,
            analytics=[],
            claimers={},
            last_creditsembed_date=datetime.now().replace(microsecond=0) - timedelta(seconds=SECONDS_DELAY),
            prompts={PROMPT1NAME: PROMPT1VALUE, PROMPT2NAME: PROMPT2VALUE, PROMPT3NAME: PROMPT3VALUE, PROMPT4NAME: PROMPT4VALUE, PROMPT5NAME: PROMPT5VALUE}
        )
        bot.platforms[new_server.id] = new_server
        def_settings = await make_settings_dict(new_server)
        db.platforms.insert_one({
            "_id": guild.id,
            "name": guild.name,
            "settings": def_settings,
            "bots": [],
            'platform_type': "server",
            'credits': new_server.credits,
            'analytics': new_server.analytics,
            'claimers': new_server.claimers,
            })
    except Exception as e:
        logger.error(f"add guild to db err: {e}")

async def make_settings_dict(server: Server) -> dict:   
    """
    Make a settings dictionary for a server
    """
    try:
        if isinstance(server, Server):
            settings_dict = {
                "user_id": 0,
                "voting_channel_id": server.voting_channel_id, 
                "last_interaction_date": server.last_interaction_date.strftime("%Y-%m-%d %H:%M:%S"),
                'adminroles': server.adminroles,
                'prompts': server.prompts
                }
        else:
            settings_dict = {
                "user_id": server.user_id,
                "voting_channel_id": 0, 
                "last_interaction_date": server.last_interaction_date.strftime("%Y-%m-%d %H:%M:%S"),
                'adminroles': [],
                'prompts': server.prompts
                }
        return settings_dict
    except Exception as e:
        logger.error(e)

async def load_platform_to_memory(platform_id, bot_platforms):
    try:
        platform = db.platforms.find_one({"_id": platform_id})
        if platform['platform_type'] == "server":
            newplatform = Server(
                id=platform['_id'], 
                name=platform['name'],
                last_interaction_date=datetime.strptime(platform['settings']['last_interaction_date'], "%Y-%m-%d %H:%M:%S"),
                waiting_for="", 
                current_cb=None,
                voting_channel_id=platform['settings']['voting_channel_id'], 
                adminroles=platform['settings']['adminroles'],
                credits=platform['credits'],
                analytics=[],
                claimers=platform['claimers'],
                last_creditsembed_date=datetime.now() - timedelta(seconds=45),
                prompts=platform['settings']['prompts']
                
            )
        bot_platforms[platform['_id']] = newplatform
        logger.info(f"{newplatform.name} - server")
        for b in platform['bots']:
            if b['name'] not in [bot.name for bot in bot_platforms[platform['_id']].chatbots]:
                if b['model'].startswith('gpt-4'):
                    our_model = "gpt-4"
                else:
                    our_model = "gpt-3.5-turbo"
                nb = ChatBot(
                    name=b['name'], channels=b['channels'], model=our_model, prompt=b['prompt'], temperature=b['temperature'], top_p=b['top_p'],
                    presence_penalty=b['presence_penalty'], frequency_penalty=b['frequency_penalty'], include_usernames=b['include_usernames'],
                    long_term_memory=b['long_term_memory'], batch_number=b['batch_number'], should_make_buttons=b['should_make_buttons'],
                    last_message=None, data_name=b['data_name'], mention_mode=b['mention_mode'], web_search=b['web_search'],
                    avatar_url=b['avatar_url'], lorebooks = b['lorebooks']
                ) 
                try:
                    nb.context=json.loads(encrypt.decrypt_string(b['context'])) # Context is encrypted for privacy reasons (and because Discord wants you to encrypt it). Decrypt it.
                except Exception as e:
                    logger.error("Decryption error. Resetting context.")
                    nb.context=[]
                logger.info(f"\tChatbot: {nb.name}")
                newplatform.chatbots.append(nb)
        return newplatform
    except Exception as e:
        logger.error(f"load platform to memory err: {e}")
        return None
    

async def load_database_to_memory(bot):
    """this function loads the database into memory, and is called when the bot starts up"""
    try:
        bot.platforms.clear()
        current_guild_ids = [guild.id for guild in bot.guilds]
        for platform in db.platforms.find():
            try:
                if platform['_id'] in current_guild_ids and platform['_id'] not in bot.platforms.keys():
                    await load_platform_to_memory(platform['_id'], bot.platforms)
            except Exception as e:
                logger.error(f"Inner load db to mem err: {type(e)} - {e}")
    except Exception as e:
        logger.error(f"load db to mem err: {e}")

async def backup_db(bot):
    logger.info("Backup started")
    key = encrypt.generate_key()
    logger.info(key)
    for server in bot.platforms.values():
        await asyncio.sleep(0.01)
        await set_platform(server)
    logger.info("Backup finished")
            
async def set_platform(platform):
    def_settings = await make_settings_dict(platform)
    botlist = [await make_bot_dict(chatbot) for chatbot in platform.chatbots]
    platform_type = "server" if isinstance(platform, Server) else "user"
    try:
        db.platforms.update_one({"_id": platform.id}, {"$set": {
                    "_id": platform.id,
                    "name": platform.name,
                    "settings": def_settings,
                    "bots": botlist,
                    'platform_type': platform_type,
                    "credits": platform.credits,
                    'claimers': platform.claimers}}, upsert=True)
        for analytic in platform.analytics:
            db.platforms.update_one({"_id": platform.id}, {"$push": {
                'analytics': analytic}})
    except Exception as e:
        logger.error(f"set platform err: {e}")
    
async def make_bot_dict(chatbot):
    # given a ChatBot, format it into a dictionary for export to the database
    return {
        'name': chatbot.name,
        "channels": chatbot.channels,
        'model': chatbot.model,
        "prompt": chatbot.prompt,
        "temperature": chatbot.temperature,
        "top_p": chatbot.top_p,
        "presence_penalty": chatbot.presence_penalty,
        "frequency_penalty": chatbot.frequency_penalty,
        "include_usernames": chatbot.include_usernames,
        "long_term_memory": chatbot.long_term_memory,
        "batch_number": chatbot.batch_number,
        "should_make_buttons": chatbot.should_make_buttons,
        "data_name": chatbot.data_name,
        "mention_mode": chatbot.mention_mode,
        "web_search":chatbot.web_search,
        "context": encrypt.encrypt_string(json.dumps(list(chatbot.context))),
        "avatar_url" : chatbot.avatar_url,
        "lorebooks": chatbot.lorebooks
        }
    
async def add_cb_to_db(platform_id, dict):
    db.platforms.update_one({"_id": platform_id}, {"$push": {"bots": dict}})
    
async def get_cb(name, chatbots):
    """
    Get the chatbot to edit
    """
    if isinstance(name, str):
        for chatbot in chatbots:
            if chatbot.name.lower() == name.strip().lower():
                return chatbot
    return None

async def remove_cb_from_db(guildid, botname):
    db.platforms.update_one({"_id": guildid}, {"$pull": {"bots": {"name": botname}}})
    
async def change_cb_setting_in_db(guildid, botname, setting, newvalue):
    db.platforms.update_one({"_id": guildid, "bots": { "$elemMatch": { "name": botname } }}, {"$set": { f"bots.$.{setting}": newvalue } })

# use mongo cleint to add the sample stuffs