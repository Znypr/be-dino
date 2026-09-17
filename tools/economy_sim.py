"""Pure reward-economy simulator for Be Dino's private alpha.

This is mechanics-test tuning, not public launch balance.
"""

TIER_NAMES = ("Common", "Uncommon", "Rare", "Epic", "Legendary")
TIER_THRESHOLDS = (1, 25, 100, 400, 1600)
RARITY_Q = 0.25
MAX_CATCH_SCORE = 5000
MUTATION_COST = 50

CHEST_THRESHOLDS = ((10, 1), (100, 2), (500, 3))
CHEST_QUANTITY_WEIGHTS = ((1, 70), (2, 25), (3, 5))


def validate_score(catch_score: int) -> None:
    if type(catch_score) is not int:
        raise TypeError("catch_score must be an integer")
    if catch_score < 0 or catch_score > MAX_CATCH_SCORE:
        raise ValueError(f"catch_score must be between 0 and {MAX_CATCH_SCORE}")


def eligible_tier_count(catch_score: int) -> int:
    validate_score(catch_score)
    return sum(catch_score >= threshold for threshold in TIER_THRESHOLDS)


def total_run_copies(catch_score: int) -> int:
    """Private-test conversion. Every +1 catch gives exactly +1 total copy."""
    validate_score(catch_score)
    return catch_score


def allocate_tiers(catch_score: int) -> tuple[int, ...]:
    """Allocate exact copies with sequential highest-averages apportionment."""
    total = total_run_copies(catch_score)
    tier_count = eligible_tier_count(catch_score)
    if total == 0 or tier_count == 0:
        return ()

    weights = [RARITY_Q ** tier for tier in range(tier_count)]
    allocated = [0] * tier_count
    for _ in range(total):
        best = max(
            range(tier_count),
            key=lambda tier: (weights[tier] / (allocated[tier] + 1), -tier),
        )
        allocated[best] += 1
    return tuple(allocated)


def earned_chests(catch_score: int) -> int:
    """Separate chest grant curve; changing this never changes run-copy totals."""
    validate_score(catch_score)
    result = 0
    for threshold, count in CHEST_THRESHOLDS:
        if catch_score >= threshold:
            result = count
    return result


def first_score_for_common_copies(target: int) -> int | None:
    if type(target) is not int or target < 0:
        raise ValueError("target must be a nonnegative integer")
    for catch_score in range(MAX_CATCH_SCORE + 1):
        tiers = allocate_tiers(catch_score)
        common = tiers[0] if tiers else 0
        if common >= target:
            return catch_score
    return None


def snapshot(catch_score: int) -> dict:
    allocation = allocate_tiers(catch_score)
    return {
        "catch_score": catch_score,
        "total_copies": total_run_copies(catch_score),
        "eligible_tiers": TIER_NAMES[: len(allocation)],
        "tier_copies": allocation,
        "chests": earned_chests(catch_score),
    }


if __name__ == "__main__":
    for score in (0, 1, 10, 25, 50, 62, 100, 400, 500, 1000, 1600, 5000):
        print(snapshot(score))
    print("first score with 50 common copies:", first_score_for_common_copies(MUTATION_COST))
