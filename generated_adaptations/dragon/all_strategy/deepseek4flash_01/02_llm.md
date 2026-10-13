**Strategy description**

The adaptation follows a simple economy/combat split:

- **Village (`assign_in_village`)**
  - Every **Warrior** is immediately sent to the **Cave**.
  - **Farmers** default to **farm** to produce wheat.
  - The strategy spawns new villagers until it has spawned at least two Farmers and two Warriors, while also keeping a small minimum alive.
    - If there are **no Warriors at all**, spawn Warriors first so the Dragon can be attacked early.
    - Otherwise, spawn Farmers first to grow wheat income, then spawn Warriors.
  - Spawning is done in batches: two Farmers per intended spawn, up to the remaining need and available wheat.
  - As a fallback, if there are still no Warriors by step 10, one Farmer is sent to the Cave to guarantee at least one attack within the first 15 steps.

- **Cave (`assign_in_cave`)**
  - Every **Warrior** is assigned to **attack**.
  - **Farmers** normally return to the **village**.
  - If there are no Warriors in the Cave and it is still early, Farmers are allowed to **attack** so that the early-attack requirement can still be met.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.last_cave_farmers = 0
        self.last_cave_warriors = 0
        self.emergency_farmer_sent = False

    def assign_in_village(self, components, environment, group_ids, step):
        village_farmers = [c for c in components if c.role == "Farmer"]
        village_warriors = [c for c in components if c.role == "Warrior"]

        F_v = len(village_farmers)
        W_v = len(village_warriors)

        total_f = F_v + self.last_cave_farmers
        total_w = W_v + self.last_cave_warriors
        wheat = environment.farm.wheat

        # All warriors go to the Cave.
        for c in village_warriors:
            environment.assign_group(c, "cave")

        # Farmers default to farming.
        farmer_group = {c: "farm" for c in village_farmers}

        # Spawn targets:
        # - at least two new farmers
        # - at least two new warriors
        # - keep a reasonable minimum alive
        need_f = max(0, 2 - self.spawned_farmers, 3 - total_f)
        need_w = max(0, 2 - self.spawned_warriors, 3 - total_w)

        spawn_type = None
        spawn_amount = 0

        # If there are no warriors yet, prioritize spawning a warrior
        # so that the Dragon is attacked early.
        if total_w == 0 and need_w > 0:
            max_by_wheat = wheat // 12
            max_by_farmers = F_v // 2
            spawn_amount = min(need_w, max_by_wheat, max_by_farmers)
            if spawn_amount > 0:
                spawn_type = "warrior"
        else:
            # We already have warriors. Grow the economy by spawning farmers first.
            if need_f > 0:
                max_by_wheat = wheat // 10
                max_by_farmers = F_v // 2
                spawn_amount = min(need_f, max_by_wheat, max_by_farmers)
                if spawn_amount > 0:
                    spawn_type = "farmer"

            # If no farmer spawn is possible/needed, try spawning warriors.
            if spawn_type is None and need_w > 0:
                max_by_wheat = wheat // 12
                max_by_farmers = F_v // 2
                spawn_amount = min(need_w, max_by_wheat, max_by_farmers)
                if spawn_amount > 0:
                    spawn_type = "warrior"

        if spawn_type == "warrior":
            # 2 farmers are needed for each warrior spawn.
            for c in village_farmers[: 2 * spawn_amount]:
                farmer_group[c] = "spawn warrior"
            self.spawned_warriors += spawn_amount
        elif spawn_type == "farmer":
            # 2 farmers are needed for each farmer spawn.
            for c in village_farmers[: 2 * spawn_amount]:
                farmer_group[c] = "spawn farmer"
            self.spawned_farmers += spawn_amount

        # Emergency fallback: still no warrior late enough to risk missing
        # the early-attack requirement. Send one farmer to attack.
        if (
            spawn_type is None
            and not self.emergency_farmer_sent
            and 10 <= step <= 14
            and total_w == 0
            and F_v >= 1
        ):
            farmer_group[village_farmers[0]] = "cave"
            self.emergency_farmer_sent = True

        # Apply explicit assignments for every farmer.
        for c, gid in farmer_group.items():
            environment.assign_group(c, gid)

    def assign_in_cave(self, components, environment, group_ids, step):
        cave_farmers = [c for c in components if c.role == "Farmer"]
        cave_warriors = [c for c in components if c.role == "Warrior"]

        self.last_cave_farmers = len(cave_farmers)
        self.last_cave_warriors = len(cave_warriors)

        # Warriors always attack.
        for c in cave_warriors:
            environment.assign_group(c, "attack")

        # Farmers normally return to the Village.
        # If there are no warriors in the Cave and it is still early,
        # let them attack to guarantee an early attack.
        for c in cave_farmers:
            if step <= 15 and len(cave_warriors) == 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```