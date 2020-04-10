from time import time
from datetime import datetime

from models.moderations import Infraction, Note
from models.mutes import Mute
from utils.base import HootPlugin
from utils.paginator import PaginatorEmbed

from disco.bot import CommandLevels
from disco.types.message import MessageEmbed
from disco.util.snowflake import to_datetime


class InfractionPlugin(HootPlugin):

    @HootPlugin.schedule(60 * 60)
    def expire_infractions(self):
        for infraction in Infraction.find_all():
            if infraction.type == "warn" and time() - infraction.date > 7.884e+6:
                infraction.delete_self()
            elif infraction.type == "strike" and time() - infraction.date > 1.577e+7:
                infraction.delete_self()

    @HootPlugin.command("history", "<member:member>", level=CommandLevels.MOD)
    def target_history(self, event, member):
        """
        ***The History Command***

        This command will get a user's infraction history and other information.

        ***Required Values***
        > __member__ **The user's full discord name, mention, or ID**
        """
        for embed in self.get_history(member, True):
            event.msg.reply(embed=embed)

    @HootPlugin.command("selfhistory", level=CommandLevels.DEFAULT)
    def self_history(self, event):
        """
        ***The Self History Command***

        This command can be used by anyone, and gets their own infraction history.
        """
        member = self.client.api.guilds_members_get(self.config['GUILD_ID'], event.author.id)  # Quick hack for DMs
        dm = event.author.open_dm()
        for embed in self.get_history(member, False):
            dm.send_message("", embed=embed)

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
        embed.set_thumbnail(url=member.user.get_avatar_url())
        embed.color = 0x6832E3
        embeds = [embed]
        if infractions:
            embed.description += """
            __**Infractions**__
            """

            infraction_base = """
            ICIN: **{}**
            Type: **{}**
            Reason: ***{}***
            Date: **{}**
            {}"""

            for i, infraction in enumerate(infractions):
                new_infraction = infraction_base.format(
                    i,
                    infraction.type,
                    infraction.reason or "",
                    datetime.utcfromtimestamp(infraction.date),
                    f"Moderator: <@{infraction.moderator}>" if show_mods else ""
                )
                if len(embeds[-1].description + new_infraction) >= 2048:
                    next_embed = MessageEmbed()
                    next_embed.color = 0x6832E3
                    next_embed.description = new_infraction
                    embeds.append(next_embed)
                else:
                    embeds[-1].description += new_infraction

        return embeds

    @HootPlugin.command("strike", "<member:member> [reason:str...]", level=CommandLevels.MOD)
    def strike_user(self, event, member, reason: str = None):
        """
        ***The Strike Command***

        This command will strike a member, and serve out the according punishment. (For serious infractions)

        ***Required Values***
        > __member__ **The user's full discord name, mention, or ID**

        **Optional Values**
        > __reason__ **The reason for the strike**
        """
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
            dm.send_message(self.config['msgs']['strike_manual'].format(
                reason=reason,
                length=self.config['auto_actions']['strike']['mute'] // 60)
            )
            self.log_action("Strike", "{t.mention} was striked for '{r}' by {m.mention}",
                            member, r=reason, m=event.author)
        else:
            dm.send_message(self.config['msgs']['strike_manual_no_reason'].format(
                length=self.config['auto_actions']['strike']['mute'] // 60)
            )
            self.log_action("Strike", "{t.mention} was striked, no reason was provided, by {m.mention}",
                            member, e=event.author)

        if len(Infraction.find(Infraction.user == member.id,
                               Infraction.type == "strike")) == self.config['strike_to_ban']:
            member.ban()
        else:
            self.execute_action(member, self.config['auto_actions']['strike'])

    @HootPlugin.command("warn", "<member:member> [reason:str...]", level=CommandLevels.MOD)
    def warn_user(self, event, member, reason: str = None):
        """
        ***The Warn Command***

        This command will warn target member, and serve out the according punishment. (For minor infractions)

        ***Required Values***
        > __member__ **The user's full discord name, mention, or ID**

        **Optional Values**
        > __reason__ **The reason for the user's warning**
        """
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
            dm.send_message(self.config['msgs']['warn'].format(reason=reason, length=self.config['auto_actions']['warn']['mute'] // 60))
            self.log_action("Warn", "{t.mention} was warned for '{r}' by {m.mention}",
                            member, r=reason, m=event.author)
        else:
            dm.send_message(self.config['msgs']['warn_no_reason'].format(length=self.config['auto_actions']['warn']['mute'] // 60))
            self.log_action("Warn", "{t.mention} was warned, no reason was provided, by {m.mention}",
                            member, e=event.author)

        if not len(Infraction.find(Infraction.user == member.id,
                                   Infraction.type == 'warn')) % self.config['warns_to_strike']:
            dm.send_message(self.config['msgs']['strike_auto'].format(length=self.config['auto_actions']['strike']['mute'] // 60))
            self.execute_action(member, self.config['auto_actions']['strike'])
        else:
            self.execute_action(member, self.config['auto_actions']['warn'])

    @HootPlugin.command("repeal", "<member:member> <ICIN:int>", level=CommandLevels.MOD)
    def repeal_infraction(self, event, member, ICIN: int):
        """
        ***The Repeal Command***

        This command will remove an infraction from a user, either a warn or a strike. Keep in mind, infractions will expire naturally so only remove if it was a mistake.

        ***Required Values***
        > __member__ **The user's full discord name, mention, or ID**

        > __ICIN__ **The infraction's ID, check history if unsure**
        """
        for i, infraction in enumerate(Infraction.find(Infraction.user == member.id)):
            if i == ICIN:
                infraction.delete_self()
                event.msg.add_reaction("👍")
                break
        else:
            event.msg.reply("ICIN does not exist for that user, sorry.")

    @HootPlugin.command("note", "<member:member> [note:str...]", level=CommandLevels.MOD)
    def append_note(self, event, member, note: str = None):
        """
        ***The Note Command***

        This command will let a moderator observe notes on a member, or add a note to a member if provided

        ***Required Values***
        > __member__ **The user's full discord name, mention, or ID**

        ***Optional Values***

        > __note__ **A note to record to that member, if provided**
        """
        if isinstance(note, str):
            Note.create(
                user=member.id,
                content=note,
                moderator=event.author.id,
                date=int(time())
            )
            event.msg.add_reaction("👍")
        else:
            notes = Note.find(Note.user == member.id)
            note_list = [""]
            for note in notes:
                if len("\n\n" + note.content + note_list[-1]) > 2048:
                    note_list.append(note.content)
                else:
                    note_list[-1] += ("\n\n" if note_list[-1] else "") + note.content

            if not notes:
                note_list[0] = "No notes exist for this user"

            PaginatorEmbed(event, note_list, title="Notes for {}".format(member.name), color=0x6832E3)

    @HootPlugin.listen("Ready")
    def schedule_unmutes(self, _):
        mutes = Mute.find_all()
        unmutes = {}
        for mute in mutes:
            if time() >= mute.end_time:
                mute.delete_self()
                if mute.target not in unmutes:
                    unmutes[mute.target] = True,
            else:
                unmutes[mute.target] = False, int(mute.end_time - time())

        def remove_mute(user: int):
            self.client.api.guilds_members_roles_remove(
                self.config['GUILD_ID'],
                user,
                self.config["MUTE_ROLE"]
            )
            return Mute.delete(Mute.target == user)

        for target, doit in unmutes.items():
            if doit[0]:
                self.client.api.guilds_members_roles_remove(self.config['GUILD_ID'], target, self.config["MUTE_ROLE"])
            else:
                self.spawn_later(doit[1], remove_mute, target)

    def execute_action(self, member, action):
        if "mute" in action:
            member.add_role(self.config["MUTE_ROLE"])
            self.spawn_later(action['mute'], self.unmute, member)
            Mute.create(target=member.id, end_time=int(time() + action['mute']))
