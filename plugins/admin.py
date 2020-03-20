from datetime import datetime

from utils.base import HootPlugin
from utils.paginator import PaginatorEmbed

from disco.bot import CommandLevels
from disco.types.message import MessageTable


class AdminPlugin(HootPlugin):

    def load(self, ctx):
        self.start_time = datetime.now()
        self._disabled = []
        self._commands = {}

    @HootPlugin.command("disable", "<plugin_name:str>", group="plugin", level=CommandLevels.MOD)
    def disable_plugin(self, event, plugin_name: str):
        try:
            plugin = self.bot.plugins[plugin_name]
        except KeyError:
            return event.msg.reply("Unable to find plugin '{}'".format(plugin_name))
        self.bot.rmv_plugin(plugin.__class__)
        self._disabled.append(plugin_name)
        for key, cmd in self._commands.items():
            if cmd.plugin.__class__.__name__ == plugin_name:
                del self._commands[key]
        event.msg.add_reaction("👍")

    @HootPlugin.command("reload", "<plugin_name:str>", group="plugin", level=CommandLevels.MOD)
    def reload_plugin(self, event, plugin_name: str):
        try:
            plugin = self.bot.plugins[plugin_name]
        except KeyError:
            return event.msg.reply("Unable to find plugin '{}'".format(plugin_name))
        self.bot.reload_plugin(plugin.__class__)
        event.msg.add_reaction("👍")

    @HootPlugin.command("enable", "<plugin_name:str> [style:str]", group="plugin", level=CommandLevels.MOD)
    def enabled_plugin(self, event, plugin_name: str, style: str="partial"):
        if style.lower() == "complete":
            self.bot.add_plugin_module(plugin_name)  # Add catch if plugin doesn't exist
            shorthand = plugin_name.split(".")[-1]
            if shorthand in self._disabled:
                self._disabled.remove(shorthand)
        else:
            for plugin_path in self.bot.config.plugins:
                if plugin_path.split('.')[-1] == plugin_name:
                    self.bot.add_plugin_module(plugin_path)
                    break
            else:
                return event.msg.reply("Unable to find plugin '{}'".format(plugin_name))
            if plugin_name in self._disabled:
                self._disabled.remove(plugin_name)
        event.msg.add_reaction("👍")

    @HootPlugin.command("disable", "<cmd_name:str> [cmd_group:str]", group="command", level=CommandLevels.MOD)
    def disable_command(self, event, cmd_name: str, cmd_group: str = None):
        found = False
        for plugin in self.bot.plugins.values():
            for command in plugin.commands:
                if command.triggers[0] == cmd_name and command.group == cmd_group:
                    plugin.commands.remove(command)
                    self._commands[(command.triggers[0], command.group)] = command
                    self.bot.recompute()
                    found = True
                    break
            if found:
                break
        else:
            return event.msg.reply("Unable to find command '{}'".format(cmd_name))
        event.msg.add_reaction("👍")

    @HootPlugin.command("enable", "<cmd_name:str> [cmd_group:str]", group="command", level=CommandLevels.MOD)
    def enable_command(self, event, cmd_name: str, cmd_group: str = None):
        if (cmd_name, cmd_group) not in self._commands:
            return event.msg.reply("Unable to find disabled command '{}'".format(cmd_name))
        cmd = self._commands.pop((cmd_name, cmd_group))
        cmd.plugin.commands.append(cmd)
        self.bot.recompute()
        event.msg.add_reaction("👍")

    @HootPlugin.command("dashboard", level=CommandLevels.MOD)
    def display_stats(self, event):
        ping = (datetime.now() - event.msg.timestamp).microseconds // 1000
        uptime = str(datetime.now() - self.start_time).split(":")
        uptime = "{} days, {} hours, {} minutes and {} seconds".format(
            *divmod(int(uptime[0]), 24),
            int(uptime[1]),
            int(float(uptime[2]))
        )
        plugin_table = MessageTable()
        plugin_table.set_header("Plugin", "Status")
        for plugin in sorted([*self.bot.plugins.keys()] + self._disabled):
            plugin_table.add(plugin, "Enabled" if plugin not in self._disabled else "Disabled")

        command_table = MessageTable()
        command_table.set_header("Command", "Group", "Plugin", "Status")
        cmds = [*self._commands.values()]
        for plugin in self.bot.plugins.values():
            cmds.extend(plugin.commands)
        cmds.sort(key=lambda x: x.triggers[0])
        for command in cmds:
            command_table.add(command.triggers[0],
                              command.group or "None",
                              command.plugin.__class__.__name__,
                              "Disabled" if command in self._commands.values() else "Enabled"
            )

        description = """Statistics:
          - Up time: {}
          - Ping: {}ms

          Plugins:
          {}

          Commands of enabled plugins:
          {}
        """.format(uptime, ping, plugin_table.compile(), command_table.compile())
        broken_up = description.split("\n")
        final_description = [""]
        for part in broken_up:
            if len(final_description[-1] + part) + 4 > 2048:
                final_description[-1] += '```'
                final_description.append("```" + part + "\n")
            else:
                final_description[-1] += part + "\n"

        PaginatorEmbed(event, final_description, title="HootBoot's Dashboard", color=0x6832E3)


