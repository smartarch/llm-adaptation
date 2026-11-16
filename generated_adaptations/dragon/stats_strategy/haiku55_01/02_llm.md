## Strategy: threshold-based eating, warrior rotation, and early reinforcement

The Dragon has 100 HP and regenerates 5 HP per step when it is not attacked. The fight therefore needs a steady stream of warrior attacks and a short time limit. The strategy has three parts.

**Village (`assign_in_village`)**
- **Meals first.** Any villager with `steps_since_meal >= 3` goes to "eat". The threshold is set below the 6-step starvation limit to leave a margin for the one-step walk between Village and Cave. Wheat is reserved for these meals before any spawning decision.
- **Early reinforcement.** During the first steps, while enough wheat is available after reserving meals, two farmers are placed in "spawn warrior" (12 wheat) to add attackers. Farmers are used for spawning so that warriors stay available for combat. Later, if wheat allows, farmers are placed in "spawn farmer" pairs (10 wheat).
- **Warriors** who are not eating are sent to "cave".
- **Remaining farmers** stay on "farm" to produce wheat.

**Cave (`assign_in_cave`)**
- **Warriors** with `steps_since_meal < 3` attack. Warriors at or above the threshold go to "village" to eat, so they never reach the starvation state, which would make them unable to deal damage.
- **Farmers** are sent back to the Village. They have only 4 HP and deal 1 damage, so they are too fragile to stay in the Cave under the Dragon's counterattacks.

Every component receives exactly one assignment in each phase, and the code only uses group IDs from the given list.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers that have not eaten for >= EAT_THRESHOLD steps eat first (wheat is reserved for meals).
    - Early in the game, spare farmers are used to spawn extra warriors (more damage to the Dragon).
    - Warriors alternate between attacking in the Cave and returning to the Village to eat before starving.
    - Farmers stay in the Village to farm wheat (they are too fragile for the Cave).
    """

    EAT_THRESHOLD = 3          # eat before reaching the 6-step starvation limit (margin for travel)
    WARRIOR_SPAWN_STEP = 15    # spawn warriors early while the Dragon can still be killed in time
    FARMER_SPAWN_STEP = 10     # cheap farmer spawns only early on
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Meals have priority: reserve wheat for them.
        eaters = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD]
        rest = [c for c in components if c.steps_since_meal < self.EAT_THRESHOLD]
        for c in eaters:
            environment.assign_group(c, "eat")
        wheat_left = wheat - len(eaters)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        # 2) Spawning with farmers (keeps warriors available for combat).
        spawn_group = set()
        if step < self.WARRIOR_SPAWN_STEP and wheat_left >= self.WARRIOR_COST and len(farmers) >= 2:
            for c in farmers[:2]:
                environment.assign_group(c, "spawn warrior")
                spawn_group.add(id(c))
            wheat_left -= self.WARRIOR_COST
        elif step < self.FARMER_SPAWN_STEP and wheat_left >= self.FARMER_COST and len(farmers) >= 2:
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
                spawn_group.add(id(c))
            wheat_left -= self.FARMER_COST

        # 3) Warriors not eating go to the Cave to fight.
        for c in warriors:
            environment.assign_group(c, "cave")

        # 4) Remaining farmers farm wheat.
        for c in farmers:
            if id(c) not in spawn_group:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD and c.hp > 0:
                # Healthy and fed warriors keep attacking the Dragon.
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                # Hungry warriors return to eat before they starve.
                environment.assign_group(c, "village")
            else:
                # Farmers are too weak for the Cave; send them back to farm.
                environment.assign_group(c, "village")
```