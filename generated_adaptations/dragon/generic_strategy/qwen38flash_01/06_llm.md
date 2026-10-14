

## Analysis and Improved Strategy

**Key realization:** Each spawn *consumes 2 villagers to produce 1*, so the total villager count can never increase — it only shrinks. Therefore the game is about converting farmers into warriors efficiently while keeping enough farmers producing wheat to fund the next spawn.

**Problems with my previous attempt:**
- The warrior cap (`< 8`) and the convoluted farmer-count condition blocked productive spawning and could leave zero wheat production.
- Spawning only capped at 2 warriors left too little sustained damage against a 50 HP dragon.

**New strategy:**
1. **Warriors** always go straight to the cave and attack every step (guaranteeing attacks from step 1, well within the 15-step requirement).
2. **Farmers** are used as spawn "parents" to manufacture warriors:
   - While we have **≥ 3 farmers** and **≥ 12 wheat**, spawn a warrior (keeping ≥ 1 farmer so wheat keeps flowing).
   - When exactly **2 farmers** remain and we have **≥ 12 wheat**, convert those last 2 farmers into a warrior. This is a net **damage gain** (+3 attack vs the 2 they provided as weak attackers) and an all-in finishing blow.
   - Any leftover farmers simply farm to accumulate wheat.
3. **Farmers never linger in the cave** — they're sent back to the village.

This aggressively funnels all population into high-damage warriors over time, producing a stronger sustained attack than the conservative "max 2 warriors" baseline, which should raise both win rate and speed.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the cave immediately to start dealing damage.
        for w in warriors:
            environment.assign_group(w, "cave")

        available = list(farmers)

        # Convert pairs of farmers into warriors while keeping at least one
        # farmer producing wheat (need >= 3 farmers to spare 2 as parents).
        while len(available) >= 3 and wheat >= 12:
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            wheat -= 12

        # All-in finishing move: if exactly 2 farmers remain and we can afford
        # it, turn them into a warrior. Net damage change is +3-2 = +1 per turn
        # (warriors hit for 3, the two farmers would only hit for 2 combined),
        # and we no longer need wheat production.
        if len(available) == 2 and wheat >= 12:
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            wheat -= 12

        # Everything left over farms to build wheat for future spawns.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors stay and attack the dragon every step.
                environment.assign_group(c, "attack")
            else:
                # A farmer in the cave is wasting wheat production; send it home.
                environment.assign_group(c, "village")
```