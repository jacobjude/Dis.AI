import logging
from discord.ext import tasks, commands
import utils.dbhandler as dbhandler
import extensions.stats as stats
from config import SUPPORT_SERVER_ID, STATS_CHANNEL_ID, VOTE_CHANNEL_ID, BOT_USER_ID

logger = logging.getLogger(__name__)
class Tasks(commands.Cog):
    """Tasks for the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_stats.start()
        self.backup_db.start()
        self.send_stats.start()
        self.clear_bingbots.start()

    @tasks.loop(minutes=30)
    async def update_stats(self):
        """Update stats every 30 minutes."""
        if not self.bot.user:
            return
        if self.bot.user.id == BOT_USER_ID:
            try:
                await self.bot.topggpy.post_guild_count()
                logger.info(f"Posted server count ({self.bot.topggpy.guild_count})")
            except Exception as e:
                logger.error(f"Failed to post server count\n{e.__class__.__name__}: {e}")
        else:
            logger.info("In test, not posting")

    @tasks.loop(minutes=30)
    async def backup_db(self):
        """Backup database every 30 minutes."""
        if not self.bot.user:
            return
        try:
            await dbhandler.backup_db(self.bot)
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")

    @tasks.loop(hours=1)
    async def send_stats(self):
        """Send stats to a private channel every 1 hour."""
        if not self.bot.user:
            logger.error("No bot user")
            return
        try:
            support_server = await self.fetch_support_server()
            stats_channel = await self.fetch_channel(support_server, STATS_CHANNEL_ID)
            votes_channel = await self.fetch_channel(support_server, VOTE_CHANNEL_ID)
            stats_str = await stats.get_all_stats(self.bot, votes_channel, hours=1)
            await stats_channel.send(f"STATISTICS (past 1 hour)\n```{stats_str}```")
        except Exception as e:
            logger.error(f"Failed to send stats: {type(e)} - {e}")

    async def fetch_support_server(self):
        try:
            return await self.bot.fetch_guild(SUPPORT_SERVER_ID)
        except Exception as e:
            logger.error(f"Failed to fetch support server: {e}")
            raise

    async def fetch_channel(self, server, channel_id):
        try:
            return await server.fetch_channel(channel_id)
        except Exception as e:
            logger.error(f"Failed to fetch channel {channel_id}: {e}")
            raise

    @tasks.loop(hours=1)
    async def clear_bingbots(self):
        """Clear bing bots every 1 hour for memory purposes"""
        logger.info("Clearing bing bots")
        try:
            with open("logs.txt", "w") as f:
                f.write("")
            print("cleared logs")
            for platform in self.bot.platforms.values():
                for chatbot in platform.chatbots:
                    chatbot.bing_bots = {}
        except Exception as e:
            print(e)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
