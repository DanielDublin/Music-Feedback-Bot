import re
import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Common suffixes/keywords on artist channel names that should be stripped
# before comparison (e.g. "John Smith Music" -> "John Smith").
_SUFFIXES = (
    "officialmusic", "officialchannel", "officialvevo",
    "music", "official", "vevo", "records", "recordings",
    "beats", "productions", "channel", "topic", "tv",
)
_SUFFIX_RE = re.compile(r"(" + "|".join(_SUFFIXES) + r")$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_TOPIC_SUFFIX = re.compile(r"\s*-\s*topic\s*$", re.IGNORECASE)

# Minimum normalised length to fuzzy-compare. Anything shorter is too
# generic and inflates false positives.
_MIN_LEN = 3

# Default similarity threshold (rapidfuzz.fuzz.ratio is 0-100).
DEFAULT_THRESHOLD = 85


def normalize(name: str) -> str:
    """Lowercase, drop "- Topic" tail, strip non-alphanumerics, strip
    artist-channel suffixes."""
    if not name:
        return ""
    s = _TOPIC_SUFFIX.sub("", name).lower()
    s = _NON_ALNUM.sub("", s)
    # Repeatedly strip suffixes so "johnofficialmusic" -> "john".
    while True:
        stripped = _SUFFIX_RE.sub("", s)
        if stripped == s or not stripped:
            break
        s = stripped
    return s


def is_match(platform_names, discord_names, threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Return True if any normalized platform name fuzzy-matches any normalized
    discord name with score >= threshold."""
    platform = {normalize(n) for n in platform_names if n}
    discord = {normalize(n) for n in discord_names if n}
    platform = {p for p in platform if len(p) >= _MIN_LEN}
    discord = {d for d in discord if len(d) >= _MIN_LEN}
    for p in platform:
        for d in discord:
            score = fuzz.ratio(p, d)
            if score >= threshold:
                logger.debug("name match %r vs %r => %d", p, d, score)
                return True
    return False


def discord_identity(author) -> list[str]:
    """Return all plausible Discord-side names for the author."""
    names = [
        getattr(author, "global_name", None),
        getattr(author, "display_name", None),
        getattr(author, "name", None),
        getattr(author, "nick", None),
    ]
    return [n for n in names if n]
