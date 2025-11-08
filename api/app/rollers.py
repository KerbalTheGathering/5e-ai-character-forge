import random
from typing import List, Tuple

def roll_4d6_drop_lowest(rng: random.Random) -> Tuple[List[int], int, int]:
    """Returns (dice_sorted, dropped_index, total_of_top3). dice_sorted is ascending."""
    dice = [rng.randint(1, 6) for _ in range(4)]
    dice_sorted = sorted(dice)  # ascending
    dropped_index = 0  # lowest is at 0
    total = sum(dice_sorted[1:])  # top 3
    return dice_sorted, dropped_index, total

def roll_ability_set(seed: int | None = None):
    rng = random.Random(seed)
    rolls = []
    scores = []
    for _ in range(6):
        dice_sorted, dropped_idx, total = roll_4d6_drop_lowest(rng)
        rolls.append({"dice": dice_sorted, "dropped_index": dropped_idx, "total": total})
        scores.append(total)
    return {"method": "4d6-drop-lowest", "seed": seed, "rolls": rolls, "scores": sorted(scores, reverse=True)}
