from config import ICON_URL, MAX_TOKENS, PROMPT1VALUE
import tiktoken
# must add web_search and should_make_buttons, lorebooks to mongodb. make websearch false by default
# Set up models
encgpt3 = tiktoken.encoding_for_model('gpt-3.5-turbo')
encgpt4 = tiktoken.encoding_for_model('gpt-4')
class ChatBot:
    """
    A class to represent a chatbot.
    """
    def __init__(self, name: str, channels: list, model: str, prompt: str, temperature: float, top_p: float, presence_penalty: float, 
                 frequency_penalty, include_usernames: bool, long_term_memory: bool, batch_number: int, should_make_buttons: bool,
                 last_message, data_name: str, mention_mode: bool, web_search: bool, context: list = None, avatar_url: str = ICON_URL, lorebooks: list = None):
        """
        Initialize a ChatBot instance.
        """
        self.name = name
        self.channels = channels
        self.model = model
        self.prompt = prompt
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.include_usernames = include_usernames
        self.long_term_memory = long_term_memory
        self.batch_number = batch_number
        self.should_make_buttons = should_make_buttons
        self.last_message = last_message
        self.data_name = data_name
        self.mention_mode = mention_mode
        self.web_search = web_search
        self.context = context if context else []
        self.avatar_url = avatar_url
        self.bing_bots = {} 
        self.lorebooks = lorebooks if lorebooks else [] # list of loerbook names

    def __str__(self):
        print(self.lorebooks)
        return f"""
                __**General Settings**__
    **Name:** {self.name}
    **Prompt:** {self.prompt}
    **Web Search:** {self.web_search}
    **Include usernames:** {self.include_usernames}
    **PDF/Youtube Video:** {self.data_name}   
    **Mention Mode:** {self.mention_mode}
    **Long Term Memory:** {self.long_term_memory}
    **Regenerate/continue/delete reactions:** {self.should_make_buttons}
    **Avatar URL:** {self.avatar_url}
    **Lorebooks:** {', '.join(self.lorebooks) if self.lorebooks else 'None'}

    __**Output Generation Settings**__
    **Model:** {self.model}
    **Temperature:** {self.temperature}
    **Presence Penalty:** {self.presence_penalty}
    **Frequency Penalty:** {self.frequency_penalty}
    **Top P:** {self.top_p}
    
    **Tokens in memory:** {round(get_tokens(self.model, self.context))}"""

    @staticmethod
    def validate_input(value, min_value, max_value):
        """
        Validate the input value.
        """
        if min_value <= value <= max_value:
            return True
        return False

def get_tokens(model, messages):
    if model.startswith("gpt-4"):
        tokens_per_message = 4
        tokens_per_name = -1
        enc = encgpt4
    elif model.startswith("gpt-3.5"):
        tokens_per_message = 3
        tokens_per_name = 1
        enc = encgpt3
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(enc.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    num_tokens += 60 # function call overhead
            
    print(f"num_tokens: {num_tokens} ({model})")
    return num_tokens

async def default_chat_bot(name: str):
    """
    Create a default chat bot.
    """
    return ChatBot(name=name, channels=[], model="gpt-3.5-turbo", prompt=PROMPT1VALUE, temperature=0.7, top_p=1, presence_penalty=0.9,
                   frequency_penalty=0.9, include_usernames=True, long_term_memory=True, batch_number=0, should_make_buttons=True, 
                   last_message=None, data_name=None, mention_mode=False, web_search=True, context=[], avatar_url=ICON_URL, lorebooks=[])

async def chatbot_clone(og: ChatBot):
    """
    Clone a chat bot. 
    og: original chatbot
    """
    return ChatBot(name=og.name, channels=og.channels, model=og.model, prompt=og.prompt, temperature=og.temperature,
                   top_p=og.top_p, presence_penalty=og.presence_penalty, frequency_penalty=og.frequency_penalty,
                   include_usernames=og.include_usernames, long_term_memory=og.long_term_memory, batch_number=og.batch_number,
                   should_make_buttons=og.should_make_buttons, last_message=og.last_message, data_name=og.data_name,
                   mention_mode=og.mention_mode, web_search=og.web_search, context=[], avatar_url=og.avatar_url, lorebooks=og.lorebooks)