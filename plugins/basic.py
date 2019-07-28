from disco.bot import Plugin, CommandLevels


class ModPlugin(Plugin):

    @Plugin.command("kick", "<target:member>", level=CommandLevels.MOD)
    def kick_user(self, event, target):
        target.kick()
        event.msg.add_reaction("👍")

    @Plugin.command("ban", "<target:member>", level=CommandLevels.MOD)
    def ban_user(self, event, target):
        target.ban()
        event.msg.add_reaction("👍")

    def unmute(self, member):
        member.remove_role(self.config["MUTE_ROLE"])

    @Plugin.command("mute", "<target:member> [length:time...]", level=CommandLevels.MOD)
    def mute_user(self, event, target, length: list = None):
        target.add_role(self.config["MUTE_ROLE"])
        event.msg.add_reaction("👍")
        if length:
            seconds = sum(length)
            self.spawn_later(seconds, self.unmute, target)

    @Plugin.command("unmute", "<target:member>", level=CommandLevels.MOD)
    def unmute_user(self, event, target):
        self.unmute(target)
        event.msg.add_reaction("👍")
