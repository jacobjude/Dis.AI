import os

async def reload_cogs(bot, load_only=False):
    load_fn = bot.load_extension if load_only else bot.reload_extension
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await load_fn(f'cogs.{filename[:-3]}')
            except Exception as e:
                print(f"Problem loading {{filename[:-3]}} cog: {e}")
                
