from time import sleep
from typing import List

from disco.types.message import MessageEmbed
from gevent.timeout import Timeout


class PaginatorEmbed:

    def __init__(self, event, contents: List[str], **kwargs):
        self.event = event
        self.contents = contents
        self.embed = MessageEmbed(**kwargs)
        self.index = 0
        self.update()
        self.msg = event.msg.reply("", embed=self.embed)
        if len(contents) != 1:
            self.msg.add_reaction("⬅")
            sleep(.2)
            self.msg.add_reaction("➡")
            sleep(.2)  # Or the bot could check to make sure it's not reacting to it's own reaction
            self.watch()

    def update(self):
        page = self.index % len(self.contents)
        self.embed.description = self.contents[page]
        self.embed.set_footer(text="Page {} / {}".format(page + 1, len(self.contents)))

    def watch(self):
        while True:
            reaction = self.event.command.plugin.wait_for_event(
                "MessageReactionAdd",
                lambda e: e.emoji.name in ("⬅", "➡"),
                message_id=self.msg.id,
                channel_id=self.msg.channel_id
            )
            try:
                event = reaction.get(timeout=self.event.command.plugin.config["PAGINATOR_TIMEOUT"])
            except Timeout:
                break

            if event.emoji.name == "➡":
                self.index += 1
            else:
                self.index -= 1

            self.update()
            self.msg.edit(embed=self.embed)
            reaction.delete()
