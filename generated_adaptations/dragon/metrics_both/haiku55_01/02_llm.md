## Adaptation strategy

The strategy has two parts, one for each phase of the game.

**In the Village:**
- **Warriors** always go to the "cave" group, so they reach the Dragon early and attack from the first cave step.
- **Farmers** are split into three roles. Two farmers are placed in "spawn farmer" to create a new Farmer, and then two more go to "spawn warrior" to create a new Warrior. Each spawn is limited to two pairs, so the game ends up with at least two new villagers of each role. Spawns only start when the farm has enough wheat (10 for farmers, 12 for warriors). All remaining farmers go to "farm" to keep producing wheat.
- Spawn counters are tracked on the instance, so the strategy does not over-spawn.

**In the Cave:**
- **Warriors** are always assigned to "attack", since they deal the most damage and the Dragon has 50 HP.
- Any **farmer** that ends up in the Cave is sent back to the "village" group, because farmers must stay in the Village.
- Every component is explicitly assigned on every step, as the rules require.

**How the requirements are met:**
- Warriors reach the Cave on the first step and attack, so the Dragon is attacked well within the first 15 steps.
- Warriors are kept in the Cave and attack every step, so most of them are in the Cave at any time.
- Farmers never enter the Cave.
- Extra Farmers and Warriors are spawned, which increases the damage pool and the chance of killing the Dragon before the 30-step limit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Warriors go to the Cave to attack.
      - Farmers are split: two farmers form a "spawn farmer" pair (up to 2 times),
        two farmers form a "spawn warrior" pair (up to 2 times), and the rest farm.
    Cave:
      - Warriors attack the Dragon every step.
      - Any farmer found in the Cave returns to the Village.
    """

    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12
    MAX_SPAWN_PAIRS_PER_ROLE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawn_farmer_pairs_issued = 0
        self.spawn_warrior_pairs_issued = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide how many farmer pairs can be used for spawning this step.
        remaining = list(farmers)

        # Spawn a new Farmer if affordable and still needed.
        if (len(remaining) >= 2
                and wheat >= self.FARMER_SPAWN_COST
                and self.spawn_farmer_pairs_issued < self.MAX_SPAWN_PAIRS_PER_ROLE):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn farmer")
            remaining = remaining[2:]
            self.spawn_farmer_pairs_issued += 1

        # Spawn a new Warrior if affordable and still needed.
        if (len(remaining) >= 2
                and wheat >= self.WARRIOR_SPAWN_COST
                and self.spawn_warrior_pairs_issued < self.MAX_SPAWN_PAIRS_PER_ROLE):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn warrior")
            remaining = remaining[2:]
            self.spawn_warrior_pairs_issued += 1

        # All other farmers keep farming.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers must never stay in the Cave.
                environment.assign_group(c, "village")
```