"""User-facing privacy commands: <MFprivacy, <MFterms, <MFoptout, <MFoptin, <MFdeletedata."""

import logging

import discord
from discord.ext import commands

from cogs.feedback_threads.modules.helpers import DiscordHelpers
from data.constants import BOT_LOG, MODERATORS_CHANNEL_ID
from ml_model import sample_store
from ml_model.sample_optout import is_opted_out, is_opted_out_on_disk, opted_out_count, set_opt_out

logger = logging.getLogger(__name__)

POLICY_URL = "https://docs.google.com/document/d/1fd3wr37RGj9nap2fABKM8T56xrv1q6L1QexlWi_bVmo/edit?usp=sharing"


class Privacy(commands.Cog):
    """Privacy policy, terms, and training-sample opt-out."""

    def __init__(self, bot):
        self.bot = bot

    async def _audit(self, title: str, member, color: discord.Color, fields: dict, channel_ids=(BOT_LOG,)):
        """Compliance trail: one embed per privacy operation (IDs and counts only, never message text)."""
        logger.info("%s | user=%s (%s) | %s", title, member, member.id, fields)
        embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member.mention}\n`{member.id}`", inline=True)
        for name, value in fields.items():
            embed.add_field(name=name, value=str(value), inline=True)
        for channel_id in channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                logger.warning("Could not post audit embed to %s", channel_id, exc_info=True)

    @commands.command(name="privacy", help="Show the bot's privacy policy and your data options.")
    async def privacy(self, ctx):
        embed = discord.Embed(
            title="Privacy & Data",
            description=(
                "Music Feedback Bot stores your user ID, points, warnings and kicks. "
                "Feedback you post with `<MFR` may be scored by a quality model, and "
                "moderator-confirmed samples (text only, no user ID) can be used to retrain it.\n\n"
                f"**[Terms of Service & Privacy Policy]({POLICY_URL})**\n\n"
                "`<MFoptout` — stop your feedback text from being saved as training data\n"
                "`<MFoptin` — allow it again\n"
                "`<MFdeletedata` — delete all your data (you will be removed from the server)"
            ),
            color=discord.Color.blurple(),
        )
        status = "opted out" if is_opted_out(ctx.author.id) else "included"
        embed.set_footer(text=f"Your training-sample status: {status}")
        await ctx.send(embed=embed)
        logger.info("<MFprivacy viewed by %s (%s)", ctx.author, ctx.author.id)

    @commands.command(name="terms", help="Show the bot's terms of use.")
    async def terms(self, ctx):
        await ctx.send(f"Terms of Service & Privacy Policy: <{POLICY_URL}>")

    @commands.guild_only()
    @commands.command(name="deletedata", aliases=["revoke"], help="Delete all your data (you will be removed from the server).")
    async def revoke(self, ctx):
        embed = discord.Embed(
            title="Delete all my data",
            description=(
                "Points, warnings and your feedback log are how the server's feedback system works, so deleting them means:\n"
                "• your points, warnings, kicks and feedback-log thread are **deleted**\n"
                "• your feedback messages that were used to improve the quality filter are **deleted**, along with those training samples\n"
                "• you are **banned** from this server\n\n"
                "If you only want to keep your feedback text out of the ML training data, use `<MFoptout` instead — "
                "no penalty, nothing else changes.\n\n"
                "Press the red button to confirm. This expires in 60 seconds."
            ),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed, view=_RevokeView(self, ctx.author))

    async def process_revocation(self, member: discord.Member, interaction: discord.Interaction):
        """Safety net: never let an unexpected error leave the member and the mods in the dark."""
        try:
            await self._process_revocation(member, interaction)
        except Exception:
            logger.error("Revocation crashed for %s", member.id, exc_info=True)
            await self._audit("Data deletion requested", member, discord.Color.red(), {
                "Result": "❌ CRASHED — state unknown, check manually (thread, points record, ban)",
            }, channel_ids=(MODERATORS_CHANNEL_ID, BOT_LOG))
            try:
                await interaction.edit_original_response(
                    content="❌ Something went wrong. A moderator has been notified and will finish your request."
                )
            except discord.HTTPException:
                pass

    async def _process_revocation(self, member: discord.Member, interaction: discord.Interaction):
        """Delete everything, then VERIFY each step and report a proof list.

        Each proof line is (symbol, text): ✅ done and verified, ➖ nothing to delete,
        ❌ failed or could not be verified (a moderator must finish it)."""
        guild = member.guild
        proof: list[tuple[str, str]] = []
        feedback_cog = self.bot.get_cog("FeedbackThreads")

        # 0. Find his training samples FIRST: attribution needs the original messages to still exist.
        sample_matches, sample_unresolved, sample_lookup_failed = [], 0, False
        try:
            all_samples = await sample_store.collect_samples(self.bot)
            sample_matches, sample_unresolved = await sample_store.find_user_messages(
                self.bot, member.id, all_samples
            )
        except Exception:
            sample_lookup_failed = True
            logger.error("Revocation: sample lookup failed for %s", member.id, exc_info=True)

        # 1. Feedback-log thread (Discord) + its SQLite mapping
        thread_id = None
        try:
            thread_id = await DiscordHelpers.get_thread_id_no_ctx(self.bot, member.id)
            if thread_id:
                thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)
                parent = thread.parent
                await thread.delete()
                if parent:
                    try:
                        msg = await parent.fetch_message(thread_id)
                        await msg.delete()
                    except discord.NotFound:
                        pass
        except discord.NotFound:
            pass  # thread already gone
        except Exception:
            logger.error("Revocation: thread deletion failed for %s", member.id, exc_info=True)

        try:
            await DiscordHelpers.delete_user_from_user_thread(self.bot, member.id)
            await DiscordHelpers.delete_user_from_db(self.bot, member.id)
        except Exception:
            logger.error("Revocation: thread mapping removal failed for %s", member.id, exc_info=True)

        if thread_id is None:
            proof.append(("➖", "Feedback-log thread: none existed"))
        else:
            try:
                await self.bot.fetch_channel(thread_id)
                proof.append(("❌", "Feedback-log thread: still exists — delete manually"))
            except discord.NotFound:
                proof.append(("✅", "Feedback-log thread: deleted (verified gone)"))
            except discord.HTTPException:
                proof.append(("❌", "Feedback-log thread: could not verify"))

        mapping_left = (
            feedback_cog is None
            or member.id in feedback_cog.user_thread
            or feedback_cog.sqlitedatabase.user_exists(member.id)
        )
        proof.append(("❌", "Thread mapping: still present — remove manually") if mapping_left
                     else ("✅", "Thread mapping (threads DB + memory): removed (verified)"))

        # 2. Points / warnings / kicks record
        try:
            had_row = await self.bot.db.user_exists(str(member.id))
            await self.bot.db.remove_user(str(member.id))
            still = await self.bot.db.user_exists(str(member.id))
        except Exception:
            logger.error("Revocation: DB removal failed for %s", member.id, exc_info=True)
            had_row, still = True, True
        if still:
            proof.append(("❌", "Points, warnings & kicks record: still present — remove manually"))
        elif had_row:
            proof.append(("✅", "Points, warnings & kicks record: deleted (verified)"))
        else:
            proof.append(("➖", "Points, warnings & kicks record: none existed"))

        # 2b. Training samples + the Discord messages they came from. Runs after the thread mapping is
        # gone, so FeedbackThreads.on_message_delete ignores these deletions (no refunds, no new thread).
        if sample_lookup_failed:
            proof.append(("❌", "Training samples: lookup failed — run /samples find and delete manually"))
        elif not sample_matches:
            proof.append(("➖", "Training samples: none found"))
        else:
            ids = {int(s["message_id"]) for s, _ in sample_matches}
            try:
                removed = await sample_store.remove_samples(self.bot, ids)
                leftover = ids & {int(s["message_id"]) for s in await sample_store.collect_samples(self.bot)}
                proof.append(("❌", f"Training samples: {len(leftover)} still present — remove manually")
                             if leftover else ("✅", f"Training samples: {removed} removed (verified)"))
            except Exception:
                logger.error("Revocation: sample removal failed for %s", member.id, exc_info=True)
                proof.append(("❌", f"Training samples: removal failed ({len(ids)} to remove manually)"))

            gone = 0
            for _, msg in sample_matches:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    logger.warning("Revocation: could not delete message %s", msg.id, exc_info=True)
                try:
                    await msg.channel.fetch_message(msg.id)
                except discord.NotFound:
                    gone += 1
                except discord.HTTPException:
                    pass
            proof.append(("✅", f"Feedback messages used for ML: {gone} of {len(sample_matches)} deleted (verified)")
                         if gone == len(sample_matches)
                         else ("❌", f"Feedback messages used for ML: only {gone} of {len(sample_matches)} deleted"))
        if sample_unresolved:
            proof.append(("ℹ️", f"{sample_unresolved} other sample(s) could not be attributed (original messages already deleted)"))

        # 3. Ban
        banned = False
        try:
            await guild.ban(member, reason="Data deletion requested via <MFdeletedata (data deleted)", delete_message_seconds=0)
            await guild.fetch_ban(member)  # raises NotFound if the ban didn't take
            banned = True
            proof.append(("✅", "Ban: applied (verified in the server ban list)"))
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            logger.warning("Revocation: ban failed/unverified for %s", member.id, exc_info=True)
            proof.append(("❌", "Ban: failed — a moderator must remove them"))

        # Ban fires on_member_ban -> db.remove_user again; idempotent.
        all_ok = all(sym != "❌" for sym, _ in proof)
        lines = "\n".join(f"{sym} {text}" for sym, text in proof)
        await self._audit(
            "Data deletion requested", member,
            discord.Color.green() if all_ok else discord.Color.red(),
            {
                "Result": "all steps verified" if all_ok else "INCOMPLETE — moderator action needed",
                "Proof": lines,
                "Joined": discord.utils.format_dt(member.joined_at, "R") if member.joined_at else "unknown",
            },
            channel_ids=(MODERATORS_CHANNEL_ID, BOT_LOG),
        )

        try:
            await interaction.edit_original_response(
                content="**Deletion report**\n" + lines
                + ("" if all_ok else "\nA moderator will finish the remaining steps.")
            )
        except discord.HTTPException:
            pass

    async def _set_and_prove(self, ctx, want_out: bool):
        title = "Training opt-out" if want_out else "Training opt-in"
        try:
            changed = set_opt_out(ctx.author.id, want_out)
        except OSError:
            logger.error("Opt-out write failed for %s", ctx.author.id, exc_info=True)
            await self._audit(title, ctx.author, discord.Color.red(), {"Result": "❌ write failed — not saved"})
            await ctx.send("❌ Couldn't save your choice. A moderator has been notified; please try again later.")
            return
        verified = is_opted_out_on_disk(ctx.author.id) == want_out
        symbol = "✅" if verified else "❌"
        state = "opted out" if want_out else "opted in"
        result = (state if changed else f"already {state}") + (" (verified saved)" if verified else " (NOT verified on disk)")
        await self._audit(title, ctx.author, discord.Color.green() if verified else discord.Color.red(), {
            "Result": f"{symbol} {result}",
            "Channel": ctx.channel.mention,
            "Total opted out": opted_out_count(),
        })
        if not verified:
            await ctx.send("❌ Your choice could not be verified as saved. A moderator has been notified.")
        elif want_out:
            await ctx.send(f"{symbol} " + ("Done — your feedback text will no longer be saved as training data."
                                          if changed else "You're already opted out."))
        else:
            await ctx.send(f"{symbol} " + ("Done — moderator-confirmed samples of your feedback may be used for training again."
                                          if changed else "You're not opted out."))

    @commands.command(name="optout", help="Stop your feedback text from being saved as ML training data.")
    async def optout(self, ctx):
        await self._set_and_prove(ctx, True)

    @commands.command(name="optin", help="Allow your feedback text to be saved as ML training data again.")
    async def optin(self, ctx):
        await self._set_and_prove(ctx, False)


class _RevokeView(discord.ui.View):
    """Two-button confirmation for <MFdeletedata. Only the requesting member can press."""

    def __init__(self, cog: "Privacy", member: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This isn't your request.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Delete all my data & leave", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Processing…", embed=None, view=None)
        await self.cog.process_revocation(self.member, interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelled. Nothing was changed.", embed=None, view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Privacy(bot))
