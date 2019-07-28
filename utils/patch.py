from disco.types.guild import GuildMember
from disco.bot.parser import TYPE_MAP


TIME_MAP = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24
}


def get_correct_level(self, actor):
    level = 0

    if actor.id in self.config.levels:
        level = self.config.levels[str(actor.id)]

    if isinstance(actor, GuildMember):
        for rid in actor.roles:
            rid = str(rid)
            if rid in self.config.levels and self.config.levels[rid] > level:
                level = self.config.levels[rid]

    return level


def get_member(ctx, data):
    if data.isdigit():
        target_id = data
    elif data.startswith("<") and data.endswith(">"):
        target_id = data.strip("<@!>")
    else:
        raise ValueError("Invalid member id / mention")
    return ctx.guild.get_member(target_id)


def get_time(_, data):
    dates = data.lower().split(" ")
    total_seconds = 0
    for date in dates:
        total_seconds += TIME_MAP[date[-1]] * int(date[:-1])
    return total_seconds


TYPE_MAP['member'] = get_member
TYPE_MAP['time'] = get_time
