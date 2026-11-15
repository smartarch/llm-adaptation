## Strategy: Rotating Warrior Strike with Scheduled Meals and Farmer Spawning

**Core idea:** Farmers never leave the Village. They farm, eat on schedule, and supply wheat for spawning. Warriors form a rotating strike team that goes to the Cave as soon as possible, attacks while their meal clock is fresh, and returns to the Village to eat before they risk starving.

**Village rules (`assign_in_village`):**
1. **Meals first.** Any villager with `steps_since_meal >= 4` is put in "eat" (a margin before the 6-step limit). Warriors that have eaten recently but are back in the Village (`steps_since_meal >= 1`) also eat, so they leave the Village fresh and go to the Cave with a meal clock near 0.
2. **Spawning with a wheat budget.** Wheat for the meals is reserved first. The remaining wheat is then used for spawning:
   - If there are fewer than 2 Farmers, spawn Farmers (10 wheat).
   - Otherwise, if there are fewer than 4 Warriors, spawn Warriors (12 wheat).
   - Spawns use two idle villagers, preferring Farmers.
3. **Warriors strike.** Fresh warriors (`steps_since_meal == 0`, i.e. never hungry) go to the "cave". Warriors that still need food are kept in the Village to eat, so no hungry warrior is sent to the Cave.
4. **Farmers farm.** All remaining farmers go to "farm".

**Cave rules (`assign_in_cave`):**
1. Farmers that somehow end up in the Cave return to the Village.
2. Warriors with `steps_since_meal >= 2` go back to the Village to eat. This keeps them under the 6-step starvation limit and makes sure they return before the 3-step threshold.
3. All other warriors attack the Dragon.
4. **Coverage guarantee.** If no warrior is eligible to attack in a given step, the warrior with the freshest meal stays and attacks. This keeps the Dragon from being unattacked for more than 2 consecutive steps, which would trigger its regeneration.

**Why it satisfies the requirements:**
- The first warriors leave for the Cave at step 1, so the Dragon is attacked well within the first 15 steps.
- Every villager eats at least every 4 to 5 steps, so none starve.
- Farmers stay in the Village and spawn both roles.
- The rotation keeps attacks nearly continuous, which limits Dragon regeneration.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers and warriors must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors in the Cave return to the Village at this meal-clock value.
    CAVE_RETURN_THRESHOLD = 2
    # Target population used to decide what to spawn.
    MIN_FARMERS = 2
    MIN_WARRIORS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Decide who eats this step (food is priority, it costs 1 wheat each).
        eaters = []
        non_eaters = []
        for c in components:
            if c.role == "Farmer":
                needs_food = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                # Warriors eat whenever they are in the Village and not fresh,
                # so they can leave for the Cave with a meal clock near 0.
                needs_food = c.steps_since_meal >= 1
            if needs_food:
                eaters.append(c)
            else:
                non_eaters.append(c)

        wheat_after_meals = wheat - len(eaters)

        # 2. Choose spawning (uses idle, non-eating villagers as the spawn pair).
        spawn_pair = []
        spawn_group = None
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]
        idle_warriors = [c for c in non_eaters if c.role == "Warrior"]

        if len(farmers) < self.MIN_FARMERS and wheat_after_meals >= 10 and len(non_eaters) >= 2:
            spawn_group = "spawn farmer"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_pair = pool[:2]
        elif len(warriors) < self.MIN_WARRIORS and wheat_after_meals >= 12 and len(non_eaters) >= 2:
            spawn_group = "spawn warrior"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_pair = pool[:2]

        spawn_ids = {id(c) for c in spawn_pair}

        # 3. Assign each villager to exactly one group.
        for c in components:
            if c in eaters:
                environment.assign_group(c, "eat")
            elif spawn_group is not None and id(c) in spawn_ids:
                environment.assign_group(c, spawn_group)
            elif c.role == "Warrior" and c.steps_since_meal == 0:
                # Fresh warriors go to the Cave to attack.
                environment.assign_group(c, "cave")
            else:
                # Farmers (and any warrior not yet ready) keep farming.
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be here; send them home.
        for c in farmers:
            environment.assign_group(c, "village")

        attackers = []
        returners = []
        for c in warriors:
            # Hungry warriors go home to eat before they starve.
            if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                returners.append(c)
            else:
                attackers.append(c)

        # Keep the Dragon attacked every step: if nobody is eligible,
        # keep the freshest warrior in the fight.
        if not attackers and returners:
            freshest = min(returners, key=lambda c: c.steps_since_meal)
            returners.remove(freshest)
            attackers.append(freshest)

        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")
```