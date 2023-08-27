import discord
from config import (
    DISCORD_INVITE,
    ICON_URL,
    CLAIM_CREDITS_AMOUNT,
    VOTE_CREDITS_AMOUNT,
    MEMORY_LENGTH,
    GPT4_RESPONSE_COST,
    UPLOAD_DATA_COST,
)

# Define color enum
class Color:
    BLUE = discord.Colour.blue()
    YELLOW = discord.Colour.yellow()

# Define helper function to create embed
def create_embed(title: str, description: str, color: discord.Colour, fields: list = None, thumbnail_url: str = ICON_URL, footer_text: str = None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_thumbnail(url=thumbnail_url)
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed

async def send_discord_invite(interaction):
    """Sends an invite to the Discord server."""
    await interaction.channel.send(embed=create_embed(
        title="Join the Dis.AI support server for more help!",
        description=DISCORD_INVITE,
        color=Color.BLUE
    ))

async def get_credits_needed_embed(chatbot, conversation_mode=False):
    """Returns an embed showing the number of credits needed."""
    description = f"**Don't worry, credits are free!**\n`/vote` and `/claim` to get up to 🪙 **x{2 * VOTE_CREDITS_AMOUNT + 2 * CLAIM_CREDITS_AMOUNT} free credits** daily!\n1 credit is 1 chatbot response\n\n**Select an option from the dropdown and click the button to continue**\n\nYou can also **purchase credits to get them instantly** without voting or claiming!\n\nType `/credits` for more info on credits and to see how many credits you have.\n\n**Select** an option below to continue."
    footer_text = f"Credits make Dis.AI free for everyone to use. Thank you for understanding!\nUse '/disable {chatbot.name}' to stop these messages." if not conversation_mode else None
    return create_embed(
        title="🔔 Credits needed",
        description=description,
        color=Color.YELLOW,
        footer_text=footer_text
    )

async def get_credits_embed(portfolio_str):
    """Returns an embed showing the credits."""
    fields = [
        ("🤝  Dis.AI Community", f"Join the Community and claim 🪙 x{CLAIM_CREDITS_AMOUNT} every 12h", False),
        ("🗳️  Vote", f"Help Dis.AI grow and earn 🪙 x{VOTE_CREDITS_AMOUNT} every 12h", False),
        ("💳 Buy", "Buy credits and receive them instantly.", False),
        ("💬 1 credit per response", "Use 1 credit to receive a response from a GPT-3.5 chatbot (including using the regeneration and continue response buttons).", False),
        (f"🧠 {GPT4_RESPONSE_COST} credits per GPT-4 response", "GPT-4 is much smarter but slower and more expensive\n(Use `/chatbot settings` to change the GPT model).", False),
        (f"📄{UPLOAD_DATA_COST} credits per PDF / YouTube Video upload", "Chat with PDFs and YouTube Videos and get detailed summaries.", False),
        ("💼  Portfolio", portfolio_str, False),
    ]
    return create_embed(
        title="🪙 Credits",
        description="**Choose an option and click on the button below** to get more credits.",
        color=Color.BLUE,
        fields=fields,
        footer_text="Credits make Dis.AI free for everyone to use. Thank you for understanding!"
    )

# Define other embeds
help_overview_embed = create_embed(
    title="Welcome to Dis.AI 👋",
    description="Make customizable, fully personalized AI chatbots with Dis.AI 🚀",
    color=Color.BLUE,
    fields=[
        ("Fully customizable  🎨", "Customize the prompt, chat with PDFs & YouTube videos, search the web, have chatbots converse with each other, and so much more!", False),
        ("Completely free  ✨", "No sign-ups or registrations; all features are completely free to use.\nView `/credits` for more.", False),
        ("Private  🥷", "Your conversations are never used for any data collection or training. [Privacy policy.](https://github.com/jacobjude/Dis.AI/blob/main/privacy.txt)", False),
        ("and more...  🔥", "Add the bot to your Discord server or try it out here to see for yourself.", False),
        ("Select a section below for more info 🛠️", "", False),
    ]
)
# Define other embeds
commands_help_embed = create_embed(
    title="🔮 Dis.AI Commands (Page 1/2)",
    color=Color.BLUE,
    description="**Select a section from the dropdown below for more info 🛠️**",
    fields=[
        ('/create', "Create a new chatbot with default settings\nUse /enable (chatbot name) to enable the chatbot in the current channel", False),
        ("/enable (chatbot name)", "Enable the chatbot in the current channel", False),
        ("/settings", "Customize your chatbots to your liking\nChoose `Chatbot settings` in the dropdown below for info on each setting", False),
        ("/listchatbots", "List all created chatbots", False),
        ("/disable (chatbot name)", "Disables the given chatbot from the current channel", False),
        ("/conversation", "Have chatbots engage in a conversation with each other", False),
        ("/credits", "View and manage credits", False),
        ("/vote", "Vote to earn free credits", False),
    ],
    footer_text="Press the button for page 2"
)

commands_help2_embed = create_embed(
    title="🔮 Dis.AI Commands (Page 2/2)",
    color=Color.BLUE,
    description="**Select a section from the dropdown below for more info 🛠️**",
    fields=[
        ("/chatbotinfo (chatbot name)", "View a chatbot's settings", False),
        ("/viewmemory (chatbot name)", "Show the message memory for the given chatbot", False),
        ("/clearmemory (chatbot name) (optional: number of messages)", "Delete the last X messages from the given chatbot's memory (leave number of messages blank to delete all)", False),
        ("/showenabledhere", "Shows all chatbots that're enabled in the current channel", False),
        ("/adminroles", "Specify admin roles. If added, only users with these roles can use commands.", False),
    ],
    footer_text="Press the button for page 1"
)

chatbot_settings_embed = create_embed(
    title="🖌️ Chatbot Settings (Page 1/2)",
    description="Use `/settings` to change the settings for a chatbot",
    color=Color.BLUE,
    fields=[
        ("Prompt", "This is where the magic happens! Customize your chatbot's personality, instructions, whatever!", False),
        ("Include Usernames", "Allows chatbots to understand usernames.", False),
        ("PDF / YouTube Video", "Let your chatbot summarize and answer questions from a PDF or YouTube video.", False),
        ("Mention Mode", "If enabled, the chatbot will only respond if it's mentioned. It will still keep track of the conversation and context in the channel it's enabled in.", False),
        ("Long Term Memory", f"Enable or disable Infinite Memory. If disabled, responses may be slightly faster, but the chatbot will only remember up to {MEMORY_LENGTH} messages at a time.", False),
        ("Web Search", "Toggle auto web search. Web searches take longer to get a response. Disable web search if the chatbot is trying to web search at bad times. ", False),
        ("Long Prompt", "Bypass Discord's character limit for prompts by uploading a .txt file.", False),
        ("Toggle reactions", "Enable or disable the regenerate/continue buttons that appear at the end of chatbot responses.", False),
    ],
    footer_text="Press the button for page 2"
)

chatbot_settings2_embed = create_embed(
    title="🖌️ Chatbot Settings (Page 2/2)",
    description="Use `/settings` to change the settings for a chatbot",
    color=Color.BLUE,
    fields=[
        ("GPT Model", "Choose the between GPT-3.5 or GPT-4 for your responses.\nGPT-4 is smarter but slower; GPT-3.5 is less smart but faster.\n(Note: GPT-4 uses more credits. See `/credits` for more)", False),
        ("Temperature", "A value between 0 and 2 that modifies 'randomness' of the output. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.", False),
        ("Presence Penalty", "Positive values penalize new tokens based on whether they appear in the text so far, increasing the chatbot's likelihood to talk about new topics. Number between -2 and 2.", False),
        ("Frequency Penalty", "Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the chatbot's likelihood to repeat the same line verbatim. Number between -2.0 and 2.0.", False),
        ("Top P", "An alternative to temperature. It's generally recommended to alter this or temperature, but not both", False),
    ],
    footer_text="Press the button for page 1"
)

vote_embed = create_embed(
    title=f"Vote for Dis.AI 📩",
    description=f"By voting for ChatGPT, you'll get the following rewards.",
    color=Color.BLUE,
    fields=[
        (f"🪙 x{VOTE_CREDITS_AMOUNT} credits ", f"Earn **{VOTE_CREDITS_AMOUNT} credits** for each vote. You can vote every 12 hours.", False),
        ("Support Dis.AI  🙏", "By voting, you help us grow and make fun, high quality chatbots accessible to everyone, for free.", False),
    ]
)

claim_embed = create_embed(
    title="🪙  Claim Free Credits",
    description=f"You can claim free credits twice every day.\nUse`/credits` for more info on credits.",
    color=Color.BLUE,
    fields=[
        ("📩 Vote for Dis.AI", f"You can vote for Dis.AI on Top.GG every 12 hours.\nClick the button below to vote and get 🪙 x{VOTE_CREDITS_AMOUNT} credits.", False),
        ("🎁 Community Claim", f"Join the Dis.AI Community Server and use `/claim` in any channel to earn 🪙 x{CLAIM_CREDITS_AMOUNT} credits.", False),
    ]
)

credits_embed = create_embed(
    title="🪙 Credits",
    description="Choose an option below to get more credits.",
    color=Color.BLUE,
    fields=[
        ("🤝  Dis.AI Community", f"Join the Community and claim **🪙 x{CLAIM_CREDITS_AMOUNT}** every 12h!", False),
        ("🗳️  Vote", f"Help Dis.AI grow and earn **🪙 x{VOTE_CREDITS_AMOUNT}** every 12h.", False),
        ("💳  Buy", f"Buy credits and receive them instantly.", False),
        ("💬  1 credit per response", "Use 1 credit to receive a response from a GPT-3.5 chatbot (including using the regeneration and continue response buttons).", False),
        (f"🧠  {GPT4_RESPONSE_COST} credits per GPT-4 response", "GPT-4 is much smarter but slower and more expensive\n(Use `/settings` to change the GPT model).", False),
        (f"📄 {UPLOAD_DATA_COST} credits per PDF / YouTube Video upload", "Chat with PDFs and YouTube Videos and get detailed summaries.", False),
    ]
)

prompt_cb_embed = create_embed(
    title="📚  Prompt Library  📚",
    description="Prompts make the magic happen  ✨\nUse prompts to customize your chatbot's personality, instructions, and behavior.\n\n**Select** a prompt from the dropdown and **press the assign button** to finish creating your chatbot.\nYou can change the prompt later from `/settings`",
    color=Color.BLUE,
    footer_text="P.S.\nJoin the community server for tons of amazing prompts!"
)