

# Critical Bug Found + Improved Strategy

## The Real Problem

**The class name was wrong!** The requirements explicitly state the class must be named `SmartAdaptation`, but I named it `SmartDragonHuntAdaptation`. This means my code was never being used at all — the simulator fell back to a default (losing) strategy. That fully explains the 0% win rate across both attempts.

## Strategic Improvements

Now that my code will actually execute, I also need a better plan to actually win:

1. **Damage math**: Dragon = 50 HP. Warrior = 3 dmg/turn. We need ~17 warrior-turns of damage minimum, more with dragon counterattacks killing some. So we need a pipeline that produces 4–6 warriors over the game.
2. **Warrior pipeline**: As soon as we have 2 farmers + 12 wheat, spawn a warrior. Repeat. Warriors are our only win condition.
3. **Farmers**: Keep at least 2 farming to generate wheat (12 wheat ÷ 2 wheat/turn = 6 turns per warrior, but we accumulate faster with more farmers).
4. **Attack discipline**: Every warrior in cave attacks (requirement). No retreating — the simulation likely doesn't reward stalling.
5. **No farmers in cave**: They produce wheat at home; sending them is a net loss.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Rule: every warrior in village must head to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # Read available wheat defensively.
        wheat = 0
        try:
            wheat = int(getattr(environment, "wheat", 0) or 0)
        except Exception:
            wheat = 0

        # Spawn priority: warriors (we need damage output to kill the dragon).
        # A spawn group needs exactly 2 farmers in it and enough wheat.
        spawn_used = 0
        if len(farmers) >= 3 and wheat >= 12:
            # Leave at least 1 farmer farming; we have 3+ so 2 can spawn.
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            spawn_used = 2

        # Remaining farmers go to farm (they generate the wheat for next spawns).
        for f in farmers[spawn_used:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Every warrior in the cave must be attacking the dragon.
        # Any non-warrior that ended up here goes back to the village.
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```

## Why This Should Win

- **Correct class name** → the simulator now actually runs my logic.
- **Fast warrior pipeline**: With 3+ farmers producing ~5 wheat/turn (3×2 minus consumption), we spawn a new warrior roughly every 2–3 turns after turn 3.
- **No wasted turns**: Warriors attack the moment they arrive in the cave; no retreat logic stalling the win.
- **Economy stays alive**: At least one farmer always farms, ensuring wheat keeps flowing for continued warrior spawning.
- **Meets all hard constraints**: warriors-in-village → cave; warriors-in-cave → attack; farmers stay in village; first cave attack happens within 1–2 turns (requirement of attacking within 15 steps is easily met).