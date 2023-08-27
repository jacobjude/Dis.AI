import logging
import discord.ui
from discord import app_commands
from discord.ext import commands
from discord import Embed, Colour, Interaction
from extensions.uiactions import CreditsView, HelpView, VoteButton, AdminRoleView
from extensions.helpers import get_platform, claim_credits
from extensions.constants import Analytics
from extensions.embeds import help_overview_embed, vote_embed, get_credits_embed
from core.Server import Server

# Set up logging
logger = logging.getLogger(__name__)

class ServerSettings(commands.Cog):
    """A cog for server settings."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adminroles", description="If admin roles are set, only users with admin roles can modify Dis.AI chatbots.")
    @app_commands.guild_only()
    async def adminroles(self, interaction: Interaction) -> None:
        """Handle admin roles command."""
        try:
            if not interaction.guild:
                await self._send_error_message(interaction, "Cannot perform this action in a DM")
                return
            elif not interaction.user.guild_permissions.administrator:
                await self._send_error_message(interaction, "Must have administrator permissions to use this")
                return
            platform = await get_platform(self.bot.platforms, interaction, Analytics.ADMINROLES.value)
            await interaction.response.send_message(embed=Embed(title="Select Option", description="", colour=Colour.blue()), view=AdminRoleView(platform), ephemeral=True)
        except Exception as error:
            logger.error(f"admin roles err: {error}")

    @app_commands.command(name="credits", description="View and purchase Dis.AI Credits")
    async def credits(self, interaction: Interaction) -> None:
        """Handle credits command."""
        try:
            platform = await get_platform(self.bot.platforms, interaction, Analytics.CREDITS.value)
            portfolio_str = self._get_portfolio_str(platform)
            embed = await get_credits_embed(portfolio_str)
            await interaction.response.send_message(embed=embed, view=CreditsView(platform), ephemeral=True)
        except Exception as error:
            logger.error(f"/credits err: {error}")

    @app_commands.command(name="help", description="Show the help page")
    async def help(self, interaction: Interaction) -> None:
        """Handle help command."""
        try:
            await interaction.response.send_message(embed=help_overview_embed, view=HelpView(), ephemeral=True)
        except Exception as error:
            logger.error(f"/help err: {error}")

    @app_commands.command(name="vote", description="Vote for Dis.AI to earn free credits")
    async def vote(self, interaction: Interaction) -> None:
        """Handle vote command."""
        try:
            platform = await get_platform(self.bot.platforms, interaction, Analytics.VOTECOMMAND.value)
            view = discord.ui.View()
            view.add_item(VoteButton(platform))
            await interaction.response.send_message(embed=vote_embed, view=view, ephemeral=True)
        except Exception as error:
            logger.error(f"/vote err: {error}")

    @app_commands.command(name="claim", description="Claim free Dis.AI credits")
    async def claim(self, interaction: Interaction) -> None:
        """Handle claim command."""
        await claim_credits(interaction, self.bot.platforms)

    async def _send_error_message(self, interaction: Interaction, description: str) -> None:
        """Send an error message."""
        await interaction.response.send_message(embed=Embed(title="Error", description=description, color=Colour.red()))

    def _get_portfolio_str(self, platform) -> str:
        """Get portfolio string."""
        if isinstance(platform, Server):
            return f"This server ({platform.name}) has **{platform.credits} credits.**"
        else:
            return f"This DM channel has **{platform.credits} credits.**"

async def setup(bot):
    await bot.add_cog(ServerSettings(bot))