## What was wrong

The Dragon was left unattacked for more than 2 steps. The old cave logic sent every hungry Warrior home at the same time, and warriors that were away could not attack. Warriors could also drift into sync, so several of them went home together and the cave went empty.

## Fix: staggered warrior rotation

**Cave phase (main change).** Warriors leave in a staggered way, so at least one warrior stays and attacks while the others eat:

- A warrior with `steps_since_meal >= 2` may leave for the Village, but only if at least one other warrior stays in the Cave to keep attacking.
- A warrior with `steps_since_meal >= 5` must leave regardless, to avoid starvation.
- Warriors are considered from most hungry to least hungry, and the count of staying warriors is updated as each one is decided.
- Farmers that end up in the Cave go back to the Village.

Because warriors return fresh after eating, the rotation keeps one attacker in the Cave in almost every step once there are at least two warriors.

**Village phase.** Largely unchanged, with one clarification:

- Villagers with `steps_since_meal >= 3` eat first, and Warriors with that hunger are never sent to the Cave.
- Warriors that are fed (or have just eaten) go back to the Cave.
- Spawning, wheat reservation, and farming are unchanged.

The limitation is that with only one warrior, a gap of up to about 3 steps can still occur during its meal trip. Spawning additional warriors early reduces this.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Villagers:
      - Anyone with steps_since_meal >= 3 eats first (keeps everyone far from the
        6-step starvation limit, and keeps hungry warriors out of the cave).
      - Fed warriors go to the cave and attack the dragon.
      - In the cave, warriors rotate: a warrior that is getting hungry leaves for
        the village only while another warrior stays behind and keeps attacking,
        so the dragon is never left unattacked for more than 2 steps.
      - Farmers stay in the village, farm, or form pairs to spawn new
        warriors (12 wheat) and new farmers (10 wheat), at least two of each.
    """

    HUNGER_THRESHOLD = 3       # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 2        # cave: a warrior may leave for food once this hungry
    FORCE_LEAVE_THRESHOLD = 5  # cave: a warrior must leave for food at this hunger
    MIN_SPAWNS = 2             # at least this many of each role should be spawned

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat, cave, farmers_free, warriors_hungry = [], [], [], []

        # 1) Decide who must eat (most hungry first)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        meals_affordable = max(0, int(wheat))
        for c in hungry:
            if len(eat) < meals_affordable or c.steps_since_meal >= 5:
                eat.append(c)
            else:
                if c.role == "Warrior":
                    warriors_hungry.append(c)
                else:
                    farmers_free.append(c)
        wheat_after_meals = wheat - len(eat)

        # 2) Non-hungry villagers
        for c in components:
            if c in eat or c in warriors_hungry or c in farmers_free:
                continue
            if c.role == "Warrior":
                cave.append(c)              # fed warriors go attack the dragon
            else:
                farmers_free.append(c)      # farmers stay in the village

        # 3) Spawning among free farmers (pairs), warriors first, then farmers
        spawn_warrior, spawn_farmer = [], []
        available = list(farmers_free)
        remaining_wheat = wheat_after_meals

        if (self.spawned_warriors < self.MIN_SPAWNS
                and remaining_wheat >= 12 and len(available) >= 2):
            spawn_warrior = available[:2]
            available = available[2:]
            remaining_wheat -= 12
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and remaining_wheat >= 10 and len(available) >= 2):
            spawn_farmer = available[:2]
            available = available[2:]
            remaining_wheat -= 10
            self.spawned_farmers += 1

        farm = available

        # 4) Issue assignments (every component must be assigned exactly once)
        for c in eat:
            environment.assign_group(c, "eat")
        for c in warriors_hungry:
            environment.assign_group(c, "eat")
        for c in cave:
            environment.assign_group(c, "cave")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in farm:
            environment.assign_group(c, "farm")

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers must not stay in the cave
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors: decide who leaves for food, keeping at least one attacker
        # in the cave unless someone is about to starve.
        staying = len(warriors)
        leaving = set()
        for w in sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True):
            s = w.steps_since_meal
            if s >= self.FORCE_LEAVE_THRESHOLD:
                leaving.add(id(w))
                staying -= 1
            elif s >= self.LEAVE_THRESHOLD and staying - 1 >= 1:
                leaving.add(id(w))
                staying -= 1

        for w in warriors:
            if id(w) in leaving:
                environment.assign_group(w, "village")   # go eat
            else:
                environment.assign_group(w, "attack")    # keep the dragon under attack
```