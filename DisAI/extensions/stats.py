import logging
from datetime import datetime, timezone, timedelta
import psutil
from core.Server import Server
from extensions.constants import Analytics

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
logger = logging.getLogger(__name__)

"""These functions were used to collect analytics (info about how people were using the bot). I planned on making graphs and stuff with them but never got around to it."""

async def get_user_count(bot, real=True):
    """Get the user count across all guilds."""
    guild_list = [(guild.name, guild.member_count) for guild in bot.guilds]
    guildcount = len(bot.guilds)
    user_count = sum(guild[1] for guild in guild_list) if real else len(bot.users) - guild_list[-1][1] - guild_list[-2][1]
    return user_count, guildcount

async def get_avg_tokens(bot):
    """Get the average number of tokens per message."""
    token_list = [analytic[2] for platform in bot.platforms.values() for analytic in platform.analytics if analytic[0] == Analytics.GOT_GPT_RESPONSE.value]
    return sum(token_list)/len(token_list) if token_list else 0


async def get_active_users(bot, datestr):
    """Get the number of active users since a given date."""
    active_guilds_user_count = 0
    active_guild_count = 0
    date = datetime.strptime(datestr, DATE_FORMAT)
    for platform in bot.platforms.values():
        if platform.last_interaction_date > date:
            try:
                guild = bot.get_guild(platform.id)
                active_guilds_user_count += guild.member_count
                active_guild_count += 1
            except:
                pass
    return active_guilds_user_count, active_guild_count


async def get_claim_stats(bot, datestr):
    """Get the number of claimers since a given date."""
    date = datetime.strptime(datestr, DATE_FORMAT)
    total_claimers = len([(platform.name, str(analytic[1])) for platform in bot.platforms.values() for analytic in platform.analytics if analytic[0] == Analytics.CREDITSCLAIM.value])
    claimers_after_date = len([(platform.name, str(analytic[1])) for platform in bot.platforms.values() for analytic in platform.analytics if analytic[0] == Analytics.CREDITSCLAIM.value and analytic[1] > date])
    total_analytics_collected = sum(len(platform.analytics) for platform in bot.platforms.values())
    return total_claimers, claimers_after_date, total_analytics_collected
    

async def get_stopusingtime(bot):
    """Get the difference between join date and last interaction date. A measure of retention."""
    time_differences = []
    for platform in bot.platforms.values():
        try:
            time_differences.append((platform.name, (platform.last_interaction_date.replace(tzinfo=timezone.utc) - bot.get_guild(platform.id).get_member(bot.user.id).joined_at).total_seconds()/3600))
        except:
            pass
    hours_sorted = sorted([x[1] for x in time_differences])
    mean = sum(hours_sorted)/len(time_differences)
    median = hours_sorted[len(time_differences)//2]
    q1 = hours_sorted[int(len(hours_sorted)*0.25)]
    q3 = hours_sorted[int(len(hours_sorted)*0.75)]
    return q1, median, q3, mean

def credits_needed_analytics(bot):
    number_of_credits_needed_msgs_sent = 0
    number_of_gpt_responses_sent = 0
    for platform in bot.platforms.values():
        for analytic in platform.analytics:
            if analytic[0] == Analytics.RAN_OUT_OF_CREDITS.value:
                number_of_credits_needed_msgs_sent += 1
            elif analytic[0] == Analytics.GOT_GPT_RESPONSE.value:
                number_of_gpt_responses_sent += 1
    return number_of_credits_needed_msgs_sent, number_of_gpt_responses_sent


async def get_all_stats(bot, votes_channel, hours=1):
    try:
        now = datetime.now()
        print("now =", now)
        
        one_hours_ago = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        print("one_hours_ago =", one_hours_ago)
        
        one_day_ago = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        print("one_day_ago =", one_day_ago)
        
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        print("seven_days_ago =", seven_days_ago)
        
        one_month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        print("one_month_ago =", one_month_ago)
        
        total_ago = (now - timedelta(days=(365*5))).strftime("%Y-%m-%d %H:%M:%S")
        print("total_ago =", total_ago)
        
        user_count, guild_count = await get_user_count(bot)
        print("user_count =", user_count)
        print("guild_count =", guild_count)
        
        avg_tokens = await get_avg_tokens(bot)
        print("avg_tokens =", avg_tokens)
        
        active_users_1h, guild_count_1h = await get_active_users(bot, one_hours_ago)
        print("active_users_1h =", active_users_1h)
        print("guild_count_1h =", guild_count_1h)
        
        active_users_1d, guild_count_1d = await get_active_users(bot, one_day_ago)
        print("active_users_1d =", active_users_1d)
        print("guild_count_1d =", guild_count_1d)
        
        active_users_7d, guild_count_7d = await get_active_users(bot, seven_days_ago)
        print("active_users_7d =", active_users_7d)
        print("guild_count_7d =", guild_count_7d)
        
        active_users_total, guild_count_total = await get_active_users(bot, total_ago)
        print("active_users_total =", active_users_total)
        print("guild_count_total =", guild_count_total)
        
        total_claimers, claimers_after_date, total_analytics_collected = await get_claim_stats(bot, total_ago)
        print("total_claimers =", total_claimers)
        print("claimers_after_date =", claimers_after_date)
        print("total_analytics_collected =", total_analytics_collected)
        
        sutq1, sutmedian, sutq3, sutmean = await get_stopusingtime(bot)
        print("sutq1 =", sutq1)
        print("sutmedian =", sutmedian)
        print("sutq3 =", sutq3)
        print("sutmean =", sutmean)
        
        number_of_credits_needed_msgs_sent, number_of_gpt_responses_sent = credits_needed_analytics(bot)
        print("number_of_credits_needed_msgs_sent =", number_of_credits_needed_msgs_sent)
        print("number_of_gpt_responses_sent =", number_of_gpt_responses_sent)
        
        vote_counter = 0
        async for message in votes_channel.history(after=datetime.now() - timedelta(hours=hours)):
            vote_counter += 1
        print("vote_counter =", vote_counter)
        
        memory_usage = psutil.Process().memory_info().rss / (1024 ** 2)  # Convert to MB
        print("memory_usage =", memory_usage)
        
        return f"""Total user count: {user_count} users across {guild_count} servers.
Users in the last {hours} hours: {active_users_1h} users across {guild_count_1h} servers.
Users in the last day: {active_users_1d} users across {guild_count_1d} servers.
Users in the last seven days: {active_users_7d} users across {guild_count_7d} servers.
Total users in the last five years: {active_users_total} users across {guild_count_total} servers.

Total analytics collected since restart: {total_analytics_collected}
Total_claimers measured since restart: {total_claimers}
Claimers after {hours} hours ago: {claimers_after_date}

Retention (hours since join date and last interaction date):
Q1: {round(sutq1, 2)} hrs, Median: {round(sutmedian, 2)} hrs, Q3: {round(sutq3, 2)} hrs, Mean: {round(sutmean, 2)} hrs

Votes in the last {hours} hours: {vote_counter}
Memory usage: {memory_usage:0.1f} MB
Average tokens since last restart: {avg_tokens:0.1f}
Number of times ran out of credits: {number_of_credits_needed_msgs_sent}
Number of GPT responses sent: {number_of_gpt_responses_sent}
"""
    except Exception as e:
        print(e)
