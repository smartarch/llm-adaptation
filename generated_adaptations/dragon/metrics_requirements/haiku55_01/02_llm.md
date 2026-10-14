## Strategy

The strategy has two phases that map onto the two assignment hooks.

**In the Village (`assign_in_village`)**
- **Warriors** all go to the Cave (`"cave"`) on every step. This satisfies the requirement that all warriors attack the Dragon, and it sends damage dealers in from step 1, so the Dragon is attacked well within the first 15 steps.
- **Farmers** stay on the farm by default (`"farm"`), so wheat keeps flowing.
- **Spawning** uses a wheat budget read from `environment.farm.wheat`. If the budget covers a warrior spawn (12 wheat), two farmers are placed in `"spawn warrior"`. If the remaining budget covers a farmer spawn (10 wheat), two more farmers go to `"spawn farmer"`. A minimum number of farmers always stays on the farm, so wheat production does not collapse. Warriors are never used for spawning, because they need to be in the Cave.

**In the Cave (`assign_in_cave`)**
- **Warriors** are all assigned to `"attack"`. Since the Dragon's counterattacks only hit at 40% and 20%, keeping every warrior attacking maximizes damage (50 HP needs about 17 warrior hits).
- **Farmers** that end up in the Cave are sent back to `"village"`. Farmers have only 4 HP and deal 1 damage, so they are a poor use of the Cave.

Every component is assigned on every step, because group assignments do not persist implicitly. Warriors stay in the Cave most of the time, since they are only moved back once they are dead (which the game removes automatically).

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors go to the Cave and attack every step.
    Farmers stay on the farm, except for a small number used to spawn
    new warriors and farmers when enough wheat is available.
    """

    MIN_FARMERS_ON_FARM = 2   # keep some wheat production going
    SPAWN_GROUP_SIZE = 2      # two villagers per spawn, as specified
    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors head to the Cave to attack the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Plan spawns using the current wheat budget.
        budget = environment.farm.wheat
        available = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Warrior spawn (uses farmers as the spawn-pool, they stay in the Village).
        if (budget >= self.WARRIOR_WHEAT_COST
                and len(available) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_ON_FARM):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_warrior_group.append(available.pop())
            budget -= self.WARRIOR_WHEAT_COST

        # Farmer spawn.
        if (budget >= self.FARMER_WHEAT_COST
                and len(available) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_ON_FARM):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_farmer_group.append(available.pop())
            budget -= self.FARMER_WHEAT_COST

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")
        # Remaining farmers keep working the farm.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers are weak in combat; send them back to the Village.
                environment.assign_group(c, "village")
```