from core.Platform import Platform
class Server(Platform):
    def __init__(self, id, name, last_interaction_date, waiting_for, current_cb, voting_channel_id, adminroles, credits, analytics, claimers, last_creditsembed_date, prompts):
        super().__init__(id, name, last_interaction_date, waiting_for, current_cb, credits, analytics, claimers, last_creditsembed_date, prompts)
        self.voting_channel_id=voting_channel_id
        self.adminroles = adminroles
        
    async def set_admin_roles(self, roles):
        for role in roles:
            if role not in self.adminroles:
                self.adminroles.append(role)
                