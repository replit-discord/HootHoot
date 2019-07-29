from time import time, sleep
from weakref import WeakValueDictionary

from disco.bot import Plugin, CommandLevels

from models.mail import MailRoom


class MailPlugin(Plugin):

    def load(self, ctx):
        self.room_greenlets = WeakValueDictionary()
        self.preping = []
        self.channel_cache = []

    def get_room(self, channel_id: int):
        if channel_id in self.channel_cache:
            return False, None

        try:
            room = MailRoom.find_one(MailRoom.channel == channel_id)
        except IndexError:
            self.channel_cache.append(channel_id)
            if len(self.channel_cache) > self.config['max_cache']:
                self.channel_cache.pop(0)
            return False, None
        return True, room

    def expire_room(self, room):
        room.delete(room.user)
        self.client.api.channels_messages_create(room.user, self.config['closing_message'])
        self.client.api.channels_delete(room.channel)

    @Plugin.command("close", "<channel:channel_id>", level=CommandLevels.MOD)
    def close_room(self, event, channel):
        try:
            room = MailRoom.find_one(MailRoom.channel == channel)
        except IndexError:
            event.msg.reply(self.config["unknown_room"])
        else:
            self.expire_room(room)

    @Plugin.listen("MessageCreate")
    def on_mod_message(self, event):
        if event.author.id == self.client.state.me.id:
            return

        if list(self.bot.get_commands_for_message(
                self.bot.config.commands_require_mention,
                self.bot.config.commands_mention_rules,
                self.bot.config.commands_prefix,
                event)):
            return

        exists, room = self.get_room(event.channel_id)
        if not exists:
            return

        self.client.api.channels_messages_create(room.user, event.content or "<No message>")
        if event.attachments:
            self.client.api.channels_messages_create(room.channel, """__**Attachments:**__
            {}""".format("\n".join([f" - {a.url}" for a in event.attachments.values()])))

    @Plugin.listen("MessageCreate")
    def on_dm_message(self, event):
        if event.channel.type != 1 or event.author.id == self.client.state.me.id:  # Not in DM or self
            return

        if event.author.id in self.preping:
            return

        if list(self.bot.get_commands_for_message(
                self.bot.config.commands_require_mention,
                self.bot.config.commands_mention_rules,
                self.bot.config.commands_prefix,
                event)):
            return

        try:
            room = MailRoom.find_one(event.channel_id)
        except IndexError:
            self.create_room(event)
        else:
            if room.channel in self.room_greenlets:  # I shouldn't need to do this, but it doesn't hurt...
                self.room_greenlets[room.channel].kill()
            self.room_greenlets[room.channel] = self.spawn_later(self.config['expiration'], self.expire_room, room)
            self.client.api.channels_messages_create(room.channel, event.content or "<No message>")
            if event.attachments:
                self.client.api.channels_messages_create(room.channel, """__**Attachments:**__
                {}""".format("\n".join([f" - {a.url}" for a in event.attachments.values()])))

    def create_room(self, msg):
        self.preping.append(msg.author.id)
        confirm = msg.reply(self.config['confirmation_message'])
        sleep(.5)
        confirm.add_reaction("✅")
        sleep(.5)
        confirm.add_reaction("❎")
        reaction_async = self.wait_for_event("MessageReactionAdd", message_id=confirm.id, user_id=msg.author.id)

        try:
            reaction = reaction_async.get(timeout=self.config["confirm_patience"]).emoji
        except TimeoutError:
            self.preping.remove(msg.author.id)
            return msg.reply(self.config["confirm_expired"])

        if reaction.name == "❎":
            self.preping.remove(msg.author.id)
            return msg.reply(self.config["ending_conv"])
        elif reaction.name != "✅":
            self.preping.remove(msg.author.id)
            return msg.reply(self.config["bad_reaction"])

        new_channel = self.client.api.guilds_channels_create(
            self.config["GUILD_ID"], 0, msg.author.username, parent_id=self.config["mail_parent"])
        new_channel.send_message("__**NEW MAIL FROM *{}***__\n\n".format(msg.author.mention) + msg.content)
        if msg.attachments:
            new_channel.send_message("""__**Attachments:**__
            {}""".format("\n".join([f" - {a.url}" for a in msg.attachments])))

        MailRoom.create(
            user=msg.channel_id,
            channel=new_channel.id,
            date=int(time()),
            message=msg.content
        )

        room = MailRoom.find_one(msg.channel_id)
        self.room_greenlets[new_channel.id] = self.spawn_later(self.config["expiration"], self.expire_room, room)
        self.preping.remove(msg.author.id)

    # TODO: Capture message edits
