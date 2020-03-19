from datetime import datetime

from disco.bot.plugin import Plugin, CommandError
from disco.bot import CommandLevels
from disco.types.message import MessageEmbed
import gevent


class HootPlugin(Plugin):
    _shallow = True

    @property
    def command_list(self):
        return map(lambda x: x.name, self.commands)

    def execute(self, event):
        """
        Executes a CommandEvent this plugin owns.
        """
        if not event.command.oob:
            self.greenlets.add(gevent.getcurrent())
        try:
            return event.command.execute(event)
        except CommandError as e:
            msg = e.args[0]
            if msg.startswith("cannot convert"):
                event.msg.reply("Invalid arguments for the given command, try .help <command> to see how to use it.")
            else:
                event.msg.reply(e.args[0])
            return False
        finally:
            self.ctx.drop()

    def get_help(self, name: str):
        try:
            cmd = next(c for c in self.commands if c.name == name)
        except StopIteration:
            return None
        return cmd.get_docstring()

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
