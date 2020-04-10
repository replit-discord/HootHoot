from time import time

from models.mutes import Mute
from utils.base import HootPlugin

from disco.bot import CommandLevels
from gevent.timeout import Timeout


class ModPlugin(HootPlugin):

    @HootPlugin.command("kick", "<target:member>", level=CommandLevels.MOD)
    def kick_user(self, event, target):
        """
        ***The Kick Command***

        This command will kick target member from the server

        ***Required Values***
        > __target__ **The user's full discord name, mention, or ID**
        """
        target.kick()
        event.msg.add_reaction("👍")
        self.log_action("Kick", "Kicked {t} from the server. Moderator: {e.author.mention}", target, e=event)

    @HootPlugin.command("ban", "<target:member>", level=CommandLevels.MOD)
    def ban_user(self, event, target):
        """
        ***The Ban Command***

        This command will ban target member from the server

        ***Required Values***
        > __target__ **The user's full discord name, mention, or ID**
        """
        target.ban()
        event.msg.add_reaction("👍")
        self.log_action("Ban", "Banned {t} from the server. Moderator: {e.author.mention}", target, e=event)

    @HootPlugin.command("mute", "<target:member> [length:time...]", level=CommandLevels.MOD)
    def mute_user(self, event, target, length: list = None):
        """
        ***The Mute Command***

        This command restrict the target's message permissions either forever, or a certain amount of time if specified.

        ***Required Values***
        > __target__ **The user's full discord name, mention, or ID**

        **Optional Values**
        > __length__ **The amount of time until unmute in discord format.
        """
        target.add_role(self.config["MUTE_ROLE"])
        event.msg.add_reaction("👍")
        if length:
            seconds = sum(length)
            self.spawn_later(seconds, self.unmute, target)
            self.log_action("Muted", "Muted {t.mention} for {s} seconds. Moderator: {e.author.mention}", target,
                            s=seconds, e=event)
            Mute.create(target=target.id, end_time=int(time() + seconds))
        else:
            Mute.create(target=target.id, end_time=time() * 2)  # This should ensure they never get unmuted, in theory?

    @HootPlugin.command("unmute", "<target:member>", level=CommandLevels.MOD)
    def unmute_user(self, event, target):
        """
        ***The Unmute Command***

        This command will great the ability to send messages to a muted user. Avoid using this on timed mutes.

        ***Required Values***
        > __target__ **The user's full discord name, mention, or ID**
        """
        self.unmute(target, force=True)
        event.msg.add_reaction("👍")

    @HootPlugin.command("badavatar", "<target:member>", level=CommandLevels.MOD)
    def block_avatar(self, event, target):
        """
        ***The Ban Avatar Command***

        This command will mute a user until they modify their avatar to something more appropriate. If they do not change after a specified amount of time, they'll need to contact a mod to be unmuted.

        ***Required Values***
        > __target__ **The user's full discord name, mention, or ID**
        """
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
        except Timeout:
            return

        self.unmute(target, force=True)
        dm.send_message(self.config["avatar_release"])

    @HootPlugin.command("jammer", "<target:member>", level=CommandLevels.TRUSTED)
    def make_jammer(self, event, target):
        """
        Gives the jam role to a person
        """
        target.add_role("688936866132656184")
        event.msg.add_reaction("👍")

    @HootPlugin.command("echo", "<channel:channel_id> <message:str...>", level=CommandLevels.MOD)
    def echo(self, event, channel: int, message: str):
        self.client.api.channels_messages_create(channel, message)

