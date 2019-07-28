from time import time
from datetime import datetime

from models.moderations import Infraction

from disco.bot import CommandLevels, Plugin
from disco.types.message import MessageEmbed
from disco.util.snowflake import to_datetime


class InfractionPlugin(Plugin):

    @Plugin.command("history", "<member:member>", level=CommandLevels.MOD)
    def target_history(self, event, member):
        embed = self.get_history(member, True)
        event.msg.reply(embed=embed)

    @Plugin.command("selfhistory", level=CommandLevels.DEFAULT)
    def self_history(self, event):
        embed = self.get_history(event.member, False)
        event.msg.reply(embed=embed)

    def get_history(self, member, show_mods: bool):
        infractions = Infraction.find(Infraction.user == member.id)
        total_warns = len([i for i in infractions if i.type == "warn"])
        active_warns = total_warns % self.config['warns_to_strike']
        active_strikes = len([i for i in infractions if i.type == "strike"]) \
                         + total_warns // self.config['warns_to_strike']

        embed = MessageEmbed()
        embed.title = member.name + "'s History"
        embed.description = f"""__**Details:**__
        
        Total Warnings: **{active_warns} / {self.config['warns_to_strike']}**
        Total Strikes: **{active_strikes} / {self.config['strike_to_ban']}**
        Strikes from Warnings: **{total_warns // self.config['warns_to_strike']}**
        Account Creation date: **{to_datetime(member.id)}**
        """
        if infractions:
            embed.description += """
            __**Infractions**__
            """

            infraction_base = """
            Type: **{}**
            Reason: ***{}***
            Date: **{}**
            {}"""

            for infraction in infractions:
                embed.description += infraction_base.format(
                    infraction.type,
                    infraction.reason or "",
                    datetime.utcfromtimestamp(infraction.date),
                    f"Moderator: <@{infraction.moderator}>" if show_mods else ""
                )

        embed.set_thumbnail(url=member.user.get_avatar_url())
        embed.color = 0x6832E3
        return embed

    @Plugin.command("strike", "<member:member> [reason:str...]", level=CommandLevels.MOD)
    def strike_user(self, event, member, reason: str = None):
        if reason is not None:
            Infraction.create(
                user=member.id,
                type="strike",
                reason=reason,
                moderator=event.author.id,
                date=int(time())
            )
        else:
            Infraction.create(
                user=member.id,
                type="strike",
                moderator=event.author.id,
                date=int(time())
            )

        event.msg.add_reaction("👍")
        dm = member.user.open_dm()

        if reason is not None:
            dm.send_message(self.config['msgs']['strike_manual'].format(reason=reason))
        else:
            dm.send_message(self.config['msgs']['strike_manual_no_reason'])

        if len(Infraction.find(Infraction.user == member.id,
                               Infraction.type == "strike")) == self.config['strike_to_ban']:
            member.ban()
        else:
            self.execute_action(member, self.config['auto_actions']['strike'])

    @Plugin.command("warn", "<member:member> [reason:str...]", level=CommandLevels.MOD)
    def warn_user(self, event, member, reason: str = None):
        if reason is not None:
            Infraction.create(
                user=member.id,
                type="warn",
                reason=reason,
                moderator=event.author.id,
                date=int(time())
            )
        else:
            Infraction.create(
                user=member.id,
                type="warn",
                moderator=event.author.id,
                date=int(time())
            )

        event.msg.add_reaction("👍")
        dm = member.user.open_dm()

        if reason is not None:
            dm.send_message(self.config['msgs']['warn'].format(reason=reason))
        else:
            dm.send_message(self.config['msgs']['warn_no_reason'])

        if not len(Infraction.find(Infraction.user == member.id,
                                   Infraction.type == 'warn')) % self.config['warns_to_strike']:
            dm.send_message(self.config['msgs']['strike_auto'])
            self.execute_action(member, self.config['auto_actions']['strike'])
        else:
            self.execute_action(member, self.config['auto_actions']['warn'])

    def unmute(self, member):
        member.remove_role(self.config["MUTE_ROLE"])

    def execute_action(self, member, action):
        if "mute" in action:
            member.add_role(self.config["MUTE_ROLE"])
            self.spawn_later(action['mute'], self.unmute, member)
