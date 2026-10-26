## Strategy: Warriors Fight, Farmers Build Up the Village

**Core idea:** Warriors do the damage (3 per attack vs. 1 for farmers), so they go straight to the Cave and attack every step. Farmers stay in the Village to produce wheat, which funds new villagers. Farmers are the only villagers who can be placed in spawn groups.

**Village phase:**
- All Warriors go to the `cave` group.
- Farmers are split between spawning and farming. Warrior spawns get priority because they cost more wheat and deal more damage. The strategy tracks the wheat budget as it commits spawns, so it never assigns a spawn it cannot pay for.
- It tries to spawn at least two Warriors and at least two Farmers over the game. Spawns use pairs of farmers, and each spawn is capped at two attempts per type.
- Any farmer not used for spawning goes to `farm`.

**Cave phase:**
- Warriors with enough HP (at least 2) attack. This starts on the first step they reach the Cave, which satisfies the early-attack requirement.
- Warriors at 1 HP go back to the Village so they are not wiped out by the Dragon's area attack.
- Farmers go back to the Village, since they only deal 1 damage and would be exposed to the Dragon.

**Assumptions:** Spawned villagers are counted optimistically. The strategy assumes a spawn succeeds when it is assigned with enough wheat, and it tracks the planned wheat spend within a step.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack the Dragon (they deal 3 damage).
    Farmers stay in the Village, farm wheat, and spawn new villagers:
    warriors are prioritized (they are the damage dealers), and both types
    are spawned at least twice over the game.
    """

    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10
    MIN_SPAWNS_PER_TYPE = 2
    MIN_WARRIOR_HP_TO_FIGHT = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: decide how many to use for spawning (in pairs).
        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Priority 1: spawn warriors (damage dealers) while budget allows.
        if (self.warriors_spawned < self.MIN_SPAWNS_PER_TYPE
                and len(available) >= 2
                and wheat >= self.WARRIOR_WHEAT_COST):
            spawn_warrior_group = available[:2]
            available = available[2:]
            wheat -= self.WARRIOR_WHEAT_COST
            self.warriors_spawned += 1

        # Priority 2: spawn farmers so both roles are represented.
        if (self.farmers_spawned < self.MIN_SPAWNS_PER_TYPE
                and len(available) >= 2
                and wheat >= self.FARMER_WHEAT_COST):
            spawn_farmer_group = available[:2]
            available = available[2:]
            wheat -= self.FARMER_WHEAT_COST
            self.farmers_spawned += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # Everyone else keeps farming.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.hp >= self.MIN_WARRIOR_HP_TO_FIGHT:
                    # Keep attacking the Dragon.
                    environment.assign_group(c, "attack")
                else:
                    # Too weak to survive another Dragon counterattack.
                    environment.assign_group(c, "village")
            else:
                # Farmers are too fragile to fight; send them home to farm.
                environment.assign_group(c, "village")
```