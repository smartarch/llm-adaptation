## Revised strategy

The first version capped spawning at two pairs per role. That left the Dragon's 50 HP to be chipped down by a small, fixed pool of warriors, and it also spent farmers on spawning without a clear plan for wheat income. The revision changes three things:

1. **Warriors are the priority.** Each Dragon hit deals 3 damage, so warriors drive the win. Whenever the farm can afford it, a pair of farmers spawns a new Warrior. The pair cap is removed, so the damage pool keeps growing.
2. **Farmers are kept for income.** The Warrior spawn needs wheat, so the code keeps a small economy. It spawns a Farmer only while there are fewer than four farmers, so early wheat production grows. Everyone else keeps farming. The farmer pair used for a spawn is rotated each step, so farming resumes right after.
3. **Cave behavior is unchanged in spirit.** Warriors attack every step, and any farmer that somehow ends up in the Cave is sent back. Every component is explicitly assigned each step, as the rules require.

The Dragon can kill at most a few villagers per step, so a larger warrior force shortens the fight and reduces the number of counterattack rounds. That should lower the average steps to win.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - All warriors go to the Cave to attack.
      - Farmers: spawn a Warrior whenever the farm has 12+ wheat and two
        farmers are available (warriors give the most damage). Spawn a Farmer
        (10 wheat) while the farmer count is below 4 to strengthen wheat income.
        All remaining farmers keep farming.
    Cave:
      - Warriors attack the Dragon every step.
      - Any farmer in the Cave is sent back to the Village.
    """

    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12
    TARGET_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior goes to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining = list(farmers)
        farmer_count = len(farmers)

        # Prefer growing the farmer economy early, then spend wheat on warriors.
        if (len(remaining) >= 2
                and farmer_count < self.TARGET_FARMERS
                and wheat >= self.FARMER_SPAWN_COST):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn farmer")
            remaining = remaining[2:]
            wheat -= self.FARMER_SPAWN_COST
        elif len(remaining) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            for f in remaining[:2]:
                environment.assign_group(f, "spawn warrior")
            remaining = remaining[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Everyone else keeps farming to produce wheat.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers must not stay in the Cave.
                environment.assign_group(c, "village")
```