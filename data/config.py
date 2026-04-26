# No imports from our own codebase — safe to import from anywhere.

# Ordered from lowest to highest (used for rank-up/rank-down comparisons)
RANK_ORDER: list[str] = [
    "Groupies",
    "Stagehands",
    "Supporting Acts",
    "Headliners",
    "MF Gilded",
    "The Real MFrs",
]

# Roles removed when a user ranks up past them
LOWER_RANKS: frozenset[str] = frozenset({"Groupies", "Stagehands", "Supporting Acts"})

# Role names used for special-case logic across the codebase
AOTW_ROLE_NAME: str = "Artist of the Week"
FANS_ROLE_NAME: str = "Fans"

# Roles skipped when determining a member's display rank
ROLES_TO_IGNORE: frozenset[str] = frozenset({"POO CAFE", "kangaroo", "emo nemo", "Event Host"})
