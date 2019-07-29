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

    @Plugin.command("badavatar", "<target:member>", level=CommandLevels.MOD)
    def block_avatar(self, event, target):
        self.mute_user(event, target)
        bad_avatar = target.user.avatar

        dm = target.user.open_dm()
        dm.send_message(self.config['avatar_notification'])

        def changed_name(update_event):
            if getattr(update_event.user, "avatar", bad_avatar) == bad_avatar:
                return False
            return True

        async_update = self.wait_for_event("PresenceUpdate", changed_name, user__id=target.id)

        try:
            async_update.get(timeout=self.config["avatar_timeout"])
        except TimeoutError:
            return

        self.unmute(target)
        dm.send_message(self.config["avatar_release"])
