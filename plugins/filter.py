from collections import Counter
import re

from utils.base import HootPlugin


from disco.types import Message


class FilterPlugin(HootPlugin):

    def load(self, ctx):
        for i, match in enumerate(self.config["regex"]):
            self.config["regex"][i] = re.compile(match)

        self.table = {}
        for char in self.config['discord_syntax'] + self.config['extra_text']:
            self.table[ord(char)] = None

    def get_words(self, sentence: str):
        content = sentence.lower().translate(self.table)
        return [s for s in content.split(" ") if s]

    def do_checks(self, msg: Message):
        try:
            for attr in dir(self):
                if attr.startswith("check"):
                    getattr(self, attr)(msg)
        except AssertionError as reason:
            return False, str(reason)
        return True, None

    def check_bad_words(self, msg: Message):
        for word in self.get_words(msg.content):
            for reg in self.config['regex']:
                assert reg.match(word) is None, "Watch your profanity {mention}"

    def check_mentions(self, msg: Message):
        assert len(msg.mentions) <= self.config['max_mentions'], "Calm down, don't spam mentions {mention} {mention}"

    def check_repeats(self, msg: Message):
        words = Counter(self.get_words(msg.content))
        if words:
            assert words.most_common(1)[0][1] <= self.config['max_word_count'], "Don't repeat messages {mention}"

    @HootPlugin.listen("MessageCreate")
    def on_message(self, event: Message):
        good, reason = self.do_checks(event)
        if not good:
            event.delete()
            r = reason.format(mention=event.author.mention)
            event.reply(r)
            self.log_action("Blocked Message", "({r}): {c}", event.member, r=r, c=event.content)
