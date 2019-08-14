from datetime import datetime

from disco.bot.plugin import Plugin
from disco.bot import CommandLevels
from disco.types.message import MessageEmbed


class HootPlugin(Plugin):
    _shallow = True

    def log_action(self, action: str, content: str, target=None, **kwargs):
        embed = MessageEmbed()
        embed.title = action + ("  | " + str(target.user)) if target is not None else ""
        embed.color = 0x6832E3
        if target is not None:
            embed.description = content.format(t=target.user, **kwargs)
            embed.set_thumbnail(url=target.user.avatar_url)
        else:
            embed.description = content.format(**kwargs)
        embed.timestamp = datetime.utcnow().isoformat()
        self.client.api.channels_messages_create(self.config["BOT_LOGGING_CHANNEL"], " ", embed=embed)
