# Discord Privileged Intents Application — Music Feedback Bot

Replace anything in [BRACKETS]. Everything below was checked against the code (bot.py, database/db.py, ml_model/feedback_monitor.py).

## Facts that drive the answers (verified in code)

| Item | Reality |
|---|---|
| Intents enabled | `members`, `message_content`, `moderation` (default intents otherwise). **No presence intent.** |
| Persistent DB | SQLite (`database/data/MF_DB.db`): `user_id, points, warnings, kicks`. Plus `feedback_threads.sqlite`: `user_id -> thread_id, ticket_counter`. **No message text.** |
| Message text stored off-Discord | **Only** `feedback_json.json`: `{message_id, feedback text, rating 0/1, timestamp}` — written only after a moderator clicks ✅/❌ on an ML prediction in the mod channel. No user ID or username is stored in that file. |
| Export flow | When `feedback_json.json` reaches 20 entries, `ExportJson.count_entries` uploads the whole file to the private `EXPORTS_CHANNEL` in Discord, pings the co-developer, then clears the local file. So the server copy is short-lived, but **the samples then live as a Discord attachment and on whoever downloads them for retraining (the co-dev's machine).** Retention there is not controlled by the bot. |
| Message text not stored | Prefix commands, promo detection, intro cleanup, etc. process text in memory only. |
| Hosting | Google Cloud VM (disk encrypted at rest by default by Google). |
| CLAUDE.md is stale | It still says MySQL; code is SQLite. Update it. |

---

## 1. What does your application do?

> Music Feedback Bot runs in a single community Discord server ([SERVER NAME]) where musicians trade constructive feedback on each other's tracks. It enforces a 1-for-1 system: a member earns a "MF Point" by posting a written critique of another member's track (`<MFR`) and spends a point to ask for feedback on their own track (`<MFS`). The bot tracks point balances, warnings and kicks; shows leaderboards and profile cards (`<MFpoints`, `<MFtop`, `/membercard`); manages role ranks; creates one private moderator-visible thread per member as an audit log of their feedback activity; keeps channels clean (removes non-conforming intro posts, flags self-promotion links in feedback channels, corrects points when a feedback message is edited or deleted); and runs temporary double-point "Prime Time" events when members submit enough quality feedback.
>
> A small scikit-learn text classifier checks whether a `<MFR` post in the audio-feedback channel is genuine, substantive feedback or low-effort spam. It only posts its verdict to a private moderator channel, where a human moderator confirms or rejects it. The bot never bans or punishes based on the model alone.
>
> The bot serves one server, is not distributed, sells nothing, and does not share data with third parties.

## 2. Public Privacy Policy
Answer **Yes** once `PRIVACY.md` is pushed to the public repo. URLs for the Developer Portal (General Information → *Terms of Service URL* and *Privacy Policy URL*):
- `https://github.com/DanielDublin/Music-Feedback-Bot/blob/master/PRIVACY.md`
- `https://github.com/DanielDublin/Music-Feedback-Bot/blob/master/TERMS.md`

The authoritative policy text is now `PRIVACY.md` (section 10 below is an older copy). Users reach it in Discord via `<MFprivacy`.

Ignore the next sentence if you already pushed: Host it as a GitHub Gist or `PRIVACY.md` in the repo and paste the URL. Discord expects this (Developer Policy requires a privacy policy for apps that process user data).

## 3. Intents to apply for
Server Members Intent + Message Content Intent. Remove Presence.

## 4. Why do you need the Guild Members intent?

> The bot needs the Server Members intent to receive `on_member_join`, `on_member_remove` and `on_member_ban` events and to resolve members that are not in cache.
> - **Join:** create the member's record (points/warnings) and check whether they were previously kicked, alerting moderators if so.
> - **Leave / ban:** reset or delete that member's stored record so we do not keep data for people who are gone.
> - **Lookups:** points, ranks, `/membercard`, feedback-thread creation and role/rank assignment all need to fetch a member by ID and read their roles, including for members who are offline or not cached. Without the intent these features fail or act on the wrong user.
> We read only user ID, display name/avatar (for the profile card) and roles. We do not use the intent to build profiles, contact members, or sell/share data.

## 5. Why do you need the Message Content intent?

> The bot's primary interface is prefix commands (`<MFR`, `<MFS`, `<MFpoints`, `<MFtop`, `<MFgenres`, `<MFsimilar`, `<MFnotes`). The message text must be readable to parse the command and, for `<MFR`, to measure and evaluate the feedback a member wrote — that is how points are earned. We cannot move this to slash commands because the feedback itself is the message in the channel, and members must be able to edit or delete it, which triggers point corrections.
> Message content is also used to:
> 1. Run the feedback-quality classifier on `<MFR` posts in the audio-feedback channel (result goes to a private moderator channel for human confirmation).
> 2. Detect the wrong command prefix and self-promotion links (SoundCloud/YouTube/Spotify) in feedback channels so moderators can act.
> 3. Remove non-conforming messages in the intros channel.
> 4. Recompute points when a message is edited or deleted.
> Message text is processed in memory. The only text we retain off-Discord is moderator-validated samples of feedback (see ML answer below).

## 6. Data-storage answers

| Question | Answer |
|---|---|
| Storing API data off-platform? | Yes |
| 30 days or less? | No (user IDs and point/warning/kick counts persist while the user is a member) |
| Encrypted at rest? | Yes — Google Cloud persistent disks are encrypted at rest by default |
| Can users opt out of message-content tracking? | **Yes** — `<MFoptout` stops their feedback text being saved as training data (implemented). Be precise: the bot still reads messages to run commands and moderation checks; opt-out covers storage/training. |
| Storing message content off-platform? | Yes (validated feedback samples only) |
| Message content ≤ 30 days? | No (samples are kept indefinitely for model retraining; anonymous, deletable on request by message link) |
| Deletion contact | `Members can request deletion at any time by DMing [YOUR_DISCORD_USERNAME] or emailing [YOUR_EMAIL]. We delete the member's database record and any stored feedback samples within 14 days.` |

## 7. Will message content be used to train ML/AI models?

Answer **Yes** (it is true) and explain precisely:

> Yes, in a limited way. We maintain one small scikit-learn model (TF-IDF + linear classifier, not an LLM, not generative) that labels `<MFR` feedback as substantive vs. low-effort. When the model posts a prediction in the private moderator channel, a moderator marks it correct/incorrect. Only after that human confirmation do we append `{message_id, feedback text, label, timestamp}` to a local JSON file on our server. Every 20 samples the file is posted to a private staff-only channel in our own server and cleared from the server, and the maintainers download it to periodically retrain the same model. No user ID or username is stored with the text. The data is never sent to a third party outside the two maintainers, never used to train any other model, and never used for anything but this server's quality check. Members may request removal of their samples (by message ID) at any time.

---

## 8. Risks Discord is likely to push back on

| # | Risk | Fix |
|---|---|---|
| R1 | **No privacy policy** — most common rejection reason. | Publish the policy below before submitting. |
| R2 | **Storing message text indefinitely** and **training an ML model on it.** Discord's Developer Policy restricts using API data for ML/AI training, and retention must be justified. I could not load the policy page (403), so **read the "machine learning/AI" and data-retention sections yourself before answering Yes.** | Safest: stop saving raw text (store only features/labels) or set a retention cap (e.g. delete samples after 12 months), and add a server rule/notice telling members that moderator-validated feedback may be used to improve the quality filter. |
| R3 | **No opt-out.** Answering "No" invites follow-up. | Cheap fix: add `<MFoptout>` that adds the user ID to a set; `feedback_monitor._handle_validation` skips saving for those users. Then answer Yes. |
| R4 | **Deletion by message ID only.** Samples have no user ID, so you can't find a member's samples by name. | Either also store a salted hash of user ID, or tell users to give the message link. |
| R5 | **"Encrypted at rest" claim** | Accurate for default GCP disk encryption; say "Google-managed disk encryption" not "CMEK" unless you configured CMEK. |
| R5b | **Samples leave the server** (exports channel + co-dev's machine). The previous draft said they stay local; that was wrong. Discord asks where API data is stored and who can access it. | Disclose it (done in sections 7 and 10). Limit the exports channel to the 2 maintainers, keep the downloaded copy encrypted/on a protected disk, and add the co-dev to the retention and deletion commitment. Deleting a member's samples means purging the file attachments in the exports channel and the local training copy. |
| R6 | **`feedback_json.json` is not in `.gitignore`** and the repo is public. | Add it (and `*.sqlite`, `database/data/`) to `.gitignore` and confirm no samples were ever committed. |
| R7 | **Screenshots missing** | See section 9. |
| R8 | `moderation` intent / audit-log use | Not privileged; no justification needed. |
| R9 | **Developer Terms: users' data must be deleted if requested, and breach notification** | The policy below commits to both. Keep Discord token and `.env` out of the repo (already ignored). |
| R10 | Over-collection | Server Members is justified, but be ready to explain why you don't just use cached members (offline lookups, join/leave events). |

## 9. Screenshots / videos to prepare (use a test guild or blur real usernames)

1. **Video 1 (30–60 s): points loop.** Post a `<MFS` with a track, then another user's `<MFR` reply; show point change via `<MFpoints`. Supports Message Content.
2. **Screenshot: ML quality check.** A prediction embed in the private mod channel with the ✅/❌ validation. Shows human-in-the-loop.
3. **Screenshot: edit/delete correction.** Feedback thread entry showing points removed after a deleted `<MFR`.
4. **Screenshot: promo/prefix detection** warning in a feedback channel.
5. **Screenshot: intro cleanup** (before/after).
6. **Video 2 (20 s): member join/leave.** A new member joins, appears in mod log (and prior-kick alert if applicable); then leaves and the record is reset. Supports Server Members.
7. **Screenshot: `/membercard` and rank assignment** (needs member/role lookup).
8. **Screenshot: privacy policy page and the deletion-request instructions** (e.g., pinned message).
9. Host media on unlisted YouTube/Imgur or a Drive link with public view.

## 10. Minimal Privacy Policy (paste into a Gist / PRIVACY.md)

```markdown
# Privacy Policy — Music Feedback Bot
Last updated: [DATE]

Music Feedback Bot ("the Bot") operates in the [SERVER NAME] Discord server only.

## What we collect
- **User ID** and, per user, a point balance, warning count and kick count.
- **Join/leave/ban events** (to update the above).
- **Thread IDs** linking a user ID to their private moderation log thread inside Discord.
- **Feedback text samples:** when a moderator confirms or rejects the Bot's quality-check prediction on a `<MFR` feedback message, we save the message text, its message ID, a 0/1 label and a timestamp (no username or user ID). Batches of these are posted to a private staff-only channel in the server and downloaded by the Bot's maintainers (two people) for retraining.
- Messages are otherwise read only to run commands and moderation checks and are not stored by the Bot.

We do not collect presence, DMs, email, IP addresses or payment data.

## How we use it
To run the feedback point system, moderation, ranks and profile cards, and to improve the Bot's feedback-quality classifier (a small non-generative model trained only on the samples above). We never sell or share data, use it for advertising, or give it to third parties. Data is not used to train any third-party or generative AI model.

## Retention
Account records are kept while you are a member and reset or deleted when you leave or are banned. Feedback samples are kept as long as needed for model training; deletable on request.

## Storage and security
Data is stored on a Google Cloud server with Google-managed encryption at rest. Access is limited to the Bot's maintainers; feedback sample batches are visible only in a private staff channel and on the maintainers' devices. If a breach affecting your data occurs we will notify the server and, where required, Discord.

## Your choices
- Opt out of sample collection: use `<MFoptout>` [if implemented] or contact us.
- Ask for access or deletion of your data, including feedback samples (send message links): DM [YOUR_DISCORD_USERNAME] or email [YOUR_EMAIL]. We respond within 14 days.

## Discord
Use of the Bot is also subject to Discord's Terms of Service and Developer Policy. 

## Contact
[YOUR_DISCORD_USERNAME] / [YOUR_EMAIL]
```

## 11. Compliance checklist (Developer Terms + Policy, from my knowledge — I could not load the pages)

- [ ] Privacy policy published and linked in the Developer Portal
- [ ] Deletion path works and is documented (user ID record, thread mapping, feedback samples)
- [ ] Remove Presence intent from application
- [ ] ML training disclosure matches reality (R2) and is permitted per policy text — read it
- [ ] Don't use API data beyond stated purposes; no selling/sharing
- [ ] Secure storage: tokens only in `.env`; rotate the token if it was ever committed
- [ ] `.gitignore` covers samples and databases
- [ ] Check server count. Under 100 servers you can toggle the privileged intents without approval (verification can be requested from 75). The 100-server line is the one that matters for intents; I said 75 earlier.
- [ ] Exports-channel access limited to maintainers; purge old export attachments per the retention cap
