from datetime import datetime
from core.ChatBot import ChatBot
class Platform():
    def __init__(self, id: int, name: str, last_interaction_date: datetime, waiting_for: str, current_cb: ChatBot, credits: int, analytics: dict, 
                 claimers: dict, last_creditsembed_date: datetime, prompts: dict):
        self.id = id
        self.name = name
        self.last_interaction_date = last_interaction_date
        self.waiting_for = waiting_for
        self.current_cb = current_cb 
        self.chatbots= []
        self.credits=credits
        self.analytics = analytics
        self.claimers=claimers
        self.last_creditsembed_date=last_creditsembed_date
        self.prompts=prompts
    
    def __str__(self):
        return f""""id": {self.id},
            "name": {self.name},
            "analytics": {self.analytics},
            "last_interaction_date": {str(self.last_interaction_date)},
            "waiting_for": {self.waiting_for},
            "current_cb": {self.current_cb},
            "chatbots": {[chatbot.name for chatbot in self.chatbots]},
            "credits": {self.credits},
            "last_creditsembed_date": {str(self.last_creditsembed_date)},
            "prompts": {[promptname for promptname in self.prompts.keys()]}"""