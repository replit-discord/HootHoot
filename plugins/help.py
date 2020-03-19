from utils.base import HootPlugin

from disco.types.message import MessageEmbed
from disco.util.sanitize import S


class HelpPlugin(HootPlugin):

    @HootPlugin.command("help", "[name:str]")
    def help_command(self, event, name: str = None):
        """
        ***The Help Command***

        This command will provide information on a certain command, or list all commands if no command is specified.

        ***Optional Values***
        > __name__ **The name of the target command**
        """
        if name is None:
            collections = [plugin.command_list for plugin in self.bot.plugins.values()]
            complete = []
            for collection in collections:
                complete.extend(collection)

            embed = MessageEmbed()
            embed.title = 'List of Commands'
            embed.color = 0x6832E3
            embed.description = ', '.join(complete)
        else:
            for plugin in self.bot.plugins.values():
                desc = plugin.get_help(name.lower())
                if desc:
                    break
            else:
                return event.msg.reply("Could not find command '{}'".format(S(name)))
            embed = MessageEmbed()
            embed.title = '**{}**'.format(name)
            embed.color = 0x6832E3
            embed.description = desc

        event.msg.reply(" ", embed=embed)
