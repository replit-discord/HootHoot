from collections import defaultdict, deque
from datetime import datetime

from disco.bot import Plugin
from disco.types.message import MessageEmbed
from holster.emitter import Priority


def space_name(name: str):
    new_text = name[0]
    for char in name[1:]:
        if char.upper() == char:
            new_text += " " + char
        else:
            new_text += char
    return new_text


to_add = set()


def logging_wrapper(*event_names: str, **kwargs):
    def function_wrapper(func):
        def wrapper(self, event):
            if not self.config['enabled'].get(event.__class__.__name__):
                return

            embed = MessageEmbed()
            embed.title = space_name(event.__class__.__name__)
            embed.color = 0x6832E3
            embed.description = ""
            embed.timestamp = datetime.utcnow().isoformat()
            data = func(self, event)
            if "thumbnail" in data:
                embed.set_thumbnail(url=data["thumbnail"])
            if "link" in data:
                embed.url = data['link']

            for part in data['parts']:
                for key, value in part.items():
                    embed.description += "**" + key.title() + ":** " + value + "\n"
                embed.description += "\n"

            self.client.api.channels_messages_create(self.config["logging_channel"], " ", embed=embed)

        for event in event_names:
            Plugin.listen(event, priority=Priority.BEFORE, **kwargs)(wrapper)

        to_add.add(wrapper)
        return wrapper
    return function_wrapper


class LoggingPlugin(Plugin):

    def load(self, ctx):
        self.msg_cache = defaultdict(lambda: deque(maxlen=self.config['max_message_cache']))
        self.channel_cache = deque(maxlen=self.config["max_channel_cache"])
        self.voice_cache = deque(maxlen=self.config['max_voice_cache'])

    def get_msg(self, channel: int, msg_id: int):
        return next((m for m in self.msg_cache[channel] if m.id == msg_id), None)

    def get_channel(self, channel: int):
        return next((c for c in self.channel_cache if c.id == channel), None)

    def get_voice(self, user_id: int):
        return next((v for v in self.voice_cache if v.user.id == user_id), None)

    @Plugin.listen("MessageUpdate")
    @Plugin.listen("MessageCreate")
    def update_cache(self, event):
        old_event = self.get_msg(event.channel_id, event.id)
        if old_event:
            self.msg_cache[event.channel_id].remove(old_event)
        else:
            if not self.get_channel(event.channel_id):
                self.channel_cache.append(event.channel)
        self.msg_cache[event.channel_id].append(event)

    @Plugin.listen("ChannelCreate")
    @Plugin.listen("ChannelUpdate")
    def update_channel(self, event):
        old_channel = self.get_channel(event.id)
        if old_channel:
            self.channel_cache.remove(old_channel)
        self.channel_cache.append(event)

    @Plugin.listen("VoiceStateUpdate")
    def update_voice_channel(self, event):
        old_state = self.get_voice(event.user.id)
        if old_state is not None:
            self.voice_cache.remove(old_state)
        if event.channel_id:
            self.voice_cache.append(event)

    @logging_wrapper("MessageDelete")
    def log_msg_delete(self, event):

        old_message = self.get_msg(event.channel_id, event.id)

        if old_message:
            self.msg_cache[event.channel_id].remove(old_message)
            return {
                "link": "https://discordapp.com/channels/" + "/".join(map(str, (old_message.guild.id,
                                                                                event.channel_id, event.id))),
                "thumbnail": old_message.author.avatar_url,
                "parts": [
                    {
                        "channel": "<#" + str(event.channel_id) + ">",
                        "author": old_message.author.mention,
                        "content": old_message.content,
                        "attachment amount": str(len(old_message.attachments)),
                        "timestamp": old_message.timestamp.isoformat(),
                    }
                ]
            }
        else:
            return {"parts": [{
                "status": "Message not cached",
                "channel": "<#" + str(event.channel_id) + ">",
            }]}

    @logging_wrapper("MessageUpdate")
    def on_msg_edit(self, event):
        payload = {
            "link": "https://discordapp.com/channel/" + "/".join(map(str, (event.guild.id,
                                                                           event.channel_id, event.id))),
            "thumbnail": event.author.avatar_url,
            "parts": [{
                "message": "*meta*",
                "channel": "<#" + str(event.channel_id) + ">",
                "author": event.author.mention
            }]
        }

        old_msg = self.get_msg(event.channel_id, event.id)
        if old_msg:
            payload['parts'].append({
                "message": "*__old__*",
                "content": old_msg.content,
                "attachment amount": str(len(old_msg.attachments)),
                "timestamp": old_msg.timestamp.isoformat()
            })

        payload['parts'].append({
            "message": "*__new__*",
            "content": event.content,
            "attachment amount": str(len(event.attachments)),
            "timestamp": event.timestamp.isoformat()
        })

        return payload

    @logging_wrapper("ChannelUpdate", "ChannelDelete", "ChannelCreate")
    def on_channel_update_or_delete(self, event):
        old_channel = self.get_channel(event.id)
        payload = {
            "link": "https://discordapp.com/channel/{}/{}".format(event.guild_id, event.id),
            "thumbnail": event.guild.icon_url,
            "parts": []
        }
        if event.__class__.__name__ == "ChannelUpdate" and old_channel:
            payload['parts'].append({
                "channel": "*__old__*",
                "name": old_channel.name,
                "topic": old_channel.topic,
                "type": str(old_channel.type).replace("_", " ").title(),
                "overwrite count": str(len(old_channel.overwrites)),
                "parent": "none" if not old_channel.parent_id else old_channel.parent.mention
            })
        payload['parts'].append({
            "channel": "*__new__*" if event.__class__.__name__ != "ChannelDelete" else "*__deleted__*",
            "name": event.name,
            "topic": event.topic,
            "type": str(event.type).replace("_", " ").title(),
            "overwrite count": str(len(event.overwrites)),
            "parent": "none" if not old_channel.parent_id else old_channel.parent.mention
        })
        return payload

    @logging_wrapper("GuildBanAdd", "GuildBanRemove", "GuildMemberAdd", "GuildMemberRemove")
    def on_guild_ban(self, event):
        return {
            "thumbnail": event.user.avatar_url,
            "parts": [{
                "name": str(event.user),
                "is bot": str(event.user.bot),
                "user id": str(event.user.id)
            }]
        }

    @logging_wrapper("GuildMemberUpdate")
    def member_updated(self, event):
        return {
            "thumbnail": event.user.avatar_url,
            "parts": [{
                "user": event.user.mention,
                "is bot": str(event.user.bot),
                "roles": ", ".join(map(str, (event.guild.roles[rid] for rid in event.roles))),
                "nick": event.nick
            }]
        }

    @logging_wrapper("VoiceStateUpdate")
    def updated_voice_state(self, event):
        old_voice = self.get_voice(event.user.id)
        if old_voice is None:
            state = "__**Joined**__"
        elif event.channel_id is not None:
            state = "__**Status Update**__"
        else:
            state = "__**Left**__"

        return {
            "thumbnail": event.user.avatar_url,
            "parts": [{
                "state": state,
                "channel": "<#" + str(event.channel_id or old_voice.channel_id) + ">",
                "user": event.user.mention,
                "is deaf": str(event.deaf or event.self_deaf),
                "is mute": str(event.mute or event.self_mute),
            }]
        }
