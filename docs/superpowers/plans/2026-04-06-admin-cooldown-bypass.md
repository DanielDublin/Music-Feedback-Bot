# Admin Cooldown Bypass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users with administrator permissions, BOT_DEV_ID, and CO_DEV_ID to bypass all command cooldowns.

**Architecture:** Create a `admin_bypass_cooldown` helper in `modules/cooldowns.py` using `commands.dynamic_cooldown`. It returns `None` (no cooldown) for admins and dev IDs, and a normal `Cooldown` object for everyone else. Replace every `@commands.cooldown` decorator across the three affected cogs with `@admin_bypass_cooldown`.

**Tech Stack:** discord.py 2.x (`commands.dynamic_cooldown`, `commands.Cooldown`)

---

### Task 1: Create the cooldown helper module

**Files:**
- Create: `modules/cooldowns.py`

- [ ] **Step 1: Create `modules/cooldowns.py`**

```python
from discord.ext import commands
from data.constants import BOT_DEV_ID, CO_DEV_ID

BYPASS_IDS = (BOT_DEV_ID, CO_DEV_ID)


def admin_bypass_cooldown(rate: int, per: float, bucket_type: commands.BucketType = commands.BucketType.user):
    """Cooldown decorator that grants admins and dev IDs a full bypass."""
    def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return None
        if ctx.author.id in BYPASS_IDS:
            return None
        return commands.Cooldown(rate, per)
    return commands.dynamic_cooldown(predicate, bucket_type)
```

- [ ] **Step 2: Commit**

```bash
git add modules/cooldowns.py
git commit -m "feat: add admin_bypass_cooldown helper using dynamic_cooldown"
```

---

### Task 2: Update `cogs/general.py`

**Files:**
- Modify: `cogs/general.py`

There are 6 cooldown decorators to replace (lines 74, 109, 141, 199, 289, 308).

- [ ] **Step 1: Add the import at the top of `cogs/general.py`**

Add after the existing imports:
```python
from modules.cooldowns import admin_bypass_cooldown
```

- [ ] **Step 2: Replace all 6 `@commands.cooldown` decorators**

Replace each occurrence of:
```python
@commands.cooldown(1, 10, commands.BucketType.user)
```
with:
```python
@admin_bypass_cooldown(1, 10)
```

Replace each occurrence of:
```python
@commands.cooldown(1, 60, commands.BucketType.user)
```
with:
```python
@admin_bypass_cooldown(1, 60)
```

- [ ] **Step 3: Commit**

```bash
git add cogs/general.py
git commit -m "feat: bypass cooldowns for admins/devs in general.py"
```

---

### Task 3: Update `cogs/guild_events.py`

**Files:**
- Modify: `cogs/guild_events.py`

- [ ] **Step 1: Add the import at the top of `cogs/guild_events.py`**

Add after the existing imports:
```python
from modules.cooldowns import admin_bypass_cooldown
```

- [ ] **Step 2: Replace the cooldown decorator (line 16)**

Replace:
```python
@commands.cooldown(1, 5, commands.BucketType.user)
```
with:
```python
@admin_bypass_cooldown(1, 5)
```

- [ ] **Step 3: Commit**

```bash
git add cogs/guild_events.py
git commit -m "feat: bypass cooldowns for admins/devs in guild_events.py"
```

---

### Task 4: Update `cogs/music.py`

**Files:**
- Modify: `cogs/music.py`

- [ ] **Step 1: Add the import at the top of `cogs/music.py`**

Add after the existing imports:
```python
from modules.cooldowns import admin_bypass_cooldown
```

- [ ] **Step 2: Replace the cooldown decorator (line 220)**

Replace:
```python
@commands.cooldown(1, 10, commands.BucketType.user)
```
with:
```python
@admin_bypass_cooldown(1, 10)
```

- [ ] **Step 3: Commit**

```bash
git add cogs/music.py
git commit -m "feat: bypass cooldowns for admins/devs in music.py"
```
