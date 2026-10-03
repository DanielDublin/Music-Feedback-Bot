# Privacy Policy — Music Feedback Bot

Last updated: 2026-10-03

Music Feedback Bot ("the Bot") operates in the Music Feedback Discord server. This policy explains what data the Bot handles, why, and how you can control it.

## What we collect
- **User ID**, plus a point balance, warning count and kick count per user.
- **Kick count:** kept so moderators can be alerted if a previously kicked person rejoins (abuse prevention). Deleting your data with `<MFdeletedata` removes you from the server, so this record cannot be used to evade a kick.
- **Join, leave and ban events**, used to create, reset or delete the record above.
- **Thread IDs** linking your user ID to a private moderation-log thread inside Discord.
- **Feedback text samples.** When a moderator confirms or rejects the Bot's quality-check prediction on a `<MFR` feedback message, we save the message text, its message ID, a 0/1 label and a timestamp. No username or user ID is stored with the text. Batches of 20 samples are posted to a private staff-only channel in the server and downloaded by the Bot's maintainers (two people) for retraining.
- **Your training opt-out choice** (user ID only), if you use `<MFoptout`.
- Message text is otherwise read only to run commands and moderation checks, and is not stored by the Bot.

We do not collect presence data, direct messages, email addresses, IP addresses or payment information.

## How we use it
- To run the feedback point system, moderation, ranks and profile cards.
- To improve the Bot's feedback-quality classifier: a small, non-generative scikit-learn model trained only on the moderator-confirmed samples above.

We never sell or share your data, use it for advertising, or give it to third parties. Data is not used to train any third-party or generative AI model.

## Retention
- Point, warning and kick records are kept while you are a member and are reset or deleted when you leave or are banned.
- Feedback samples are kept for as long as they are needed to train and improve the Bot's feedback-quality filter. They contain no user ID or username. You can ask for your samples to be deleted at any time by sending the message link(s) (see "Your choices"), and you can stop future collection with `<MFoptout`.

## Storage and security
Data is stored on a Google Cloud server with Google-managed encryption at rest. Access is limited to the Bot's maintainers. Sample batches are visible only in a private staff channel and on the maintainers' devices. If a breach affecting your data occurs, we will notify the server and, where required, Discord.

## Your choices
- **Stop training use (optional, no penalty):** type `<MFoptout` in the server. Your feedback is still scored for moderation, but its text is no longer saved. `<MFoptin` reverses this.
- **Access or deletion:** message a moderator or the server owner on Discord (or open a ticket in the server). For feedback samples, send the message link(s). We respond within 14 days and delete your record and any stored samples we can identify.
- **Delete all your data:** type `<MFdeletedata` and confirm. We delete your points, warnings and kicks record, your private feedback-log thread, and the feedback messages of yours that were used for training together with those training samples, and you are banned from the server, because the points system is how the server works and cannot run without them.
- Type `<MFprivacy` in the server to see this information.

## Discord
Use of the Bot is also subject to Discord's [Terms of Service](https://discord.com/terms) and [Developer Policy](https://support-dev.discord.com/hc/articles/8563934450327-Discord-Developer-Policy).

## Changes
We will update the date above when this policy changes.

## Contact
a moderator or the server owner, by Discord direct message
