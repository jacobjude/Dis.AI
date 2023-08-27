import asyncio
import logging
import psutil
from time import perf_counter
from config import DISCORD_TOKEN, APPLICATION_ID
import DisAI
import utils.events as events
from utils import adminutils
from utils.dbhandler import add_guild_to_db

MB_FACTOR = float(1 << 20)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="logs.txt"
)

def log_memory_usage():
    """Logs the current memory usage."""
    memory_usage = psutil.Process().memory_info().rss / MB_FACTOR
    logging.info(f"Memory usage: {memory_usage:.2f} MB")

def log_time_taken(start_time, message):
    """Logs the time taken for a process."""
    end_time = perf_counter()
    logging.info(f"{message} {end_time-start_time} seconds")

async def main():
    """Main function to run the bot."""
    bot = DisAI.DisAI(app_id=APPLICATION_ID)

    @bot.event
    async def on_guild_join(guild):
        """Event handler for when a guild joins."""
        logging.info(f"New guild joined: {guild.name}")
        if guild.id not in bot.platforms:
            await add_guild_to_db(bot, guild)
        else:
            logging.info("Guild is already in platforms")

    @bot.event
    async def on_message(message):
        """Event handler for when a message is received."""
        await events.on_message(bot, message)

    @bot.event
    async def on_raw_reaction_add(payload):
        """Event handler for when a reaction is added."""
        await events.on_raw_reaction_add(bot, payload)

    @bot.event
    async def on_guild_remove(guild):
        """Event handler for when a guild is removed."""
        logging.info(f"Guild removed: {guild.name}")
        try:
            await events.on_guild_remove(bot, guild)
        except Exception as e:
            logging.error(f"Error in on_guild_remove: {e}")

    @bot.event
    async def on_ready():
        """Event handler for when the bot is ready."""
        await events.on_ready(bot)

    @bot.event
    async def on_dbl_vote(data):
        """Event handler for when a vote is received."""
        logging.info(f"Received a vote:\n{data}")
        if data["type"] == "test":
            return bot.dispatch("dbl_test", data)

    logging.info("Running main(). Reload_cogs")
    await adminutils.reload_cogs(bot, load_only=True)
    logging.info("Loaded cogs. Running bot. Start")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
