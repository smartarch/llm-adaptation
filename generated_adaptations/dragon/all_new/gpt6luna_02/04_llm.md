The main fixes are to assign every villager exactly once and to avoid repeatedly sending Warriors to the Cave when they are too hungry to complete multiple attacks. Cave Warriors now return at hunger 4, while Village villagers eat at that threshold. Farmers remain in the Village to sustain food production; spawning is prioritized when there are enough resources and available villagers.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, group_name):
        if group_name in group_ids:
            environment.assign_group(component, group_name)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = getattr(environment.dragon, "hp", 0)
        all_farmers = list(getattr(environment, "farmers", []))
        all_warriors = list(getattr(environment, "warriors", []))

        farmers_available = [
            v for v in villagers if getattr(v, "role", "") == "Farmer"
        ]
        warriors_available = [
            v for v in villagers if getattr(v, "role", "") == "Warrior"
        ]

        assigned = set()

        # Feed before hunger reaches the starvation threshold.
        hungry = sorted(
            villagers,
            key=lambda v: getattr(v, "steps_since_meal", 0),
            reverse=True,
        )
        for villager in hungry:
            if getattr(villager, "steps_since_meal", 0) >= 4 and wheat >= 1:
                self._assign(environment, villager, group_ids, "eat")
                assigned.add(id(villager))
                wheat -= 1

        remaining = [v for v in villagers if id(v) not in assigned]
        remaining_farmers = [
            v for v in remaining if getattr(v, "role", "") == "Farmer"
        ]
        remaining_warriors = [
            v for v in remaining if getattr(v, "role", "") == "Warrior"
        ]

        # Spawn one Farmer early if the settlement has fewer than three.
        # When there are no Warriors yet, secure a Warrior first unless food
        # stocks are ample enough to afford both opportunities.
        total_warriors = len(all_warriors)
        total_farmers = len(all_farmers)
        spawn_group = None
        spawn_pair = []

        can_spawn_farmer = total_farmers < 3 and wheat >= 10
        can_spawn_warrior = wheat >= 12

        if can_spawn_farmer and (total_warriors > 0 or wheat >= 22):
            spawn_group = "spawn farmer"
            candidates = remaining_farmers + remaining_warriors
        elif can_spawn_warrior and total_warriors == 0:
            spawn_group = "spawn warrior"
            candidates = remaining_farmers + remaining_warriors
        elif (
            can_spawn_warrior
            and dragon_hp > 0
            and total_farmers > 2
            and len(remaining_farmers) >= 2
        ):
            # Preserve at least two Farmers for food production.
            spawn_group = "spawn warrior"
            candidates = remaining_farmers
        else:
            candidates = []

        if spawn_group and len(candidates) >= 2:
            spawn_pair = candidates[:2]
            for villager in spawn_pair:
                self._assign(environment, villager, group_ids, spawn_group)
                assigned.add(id(villager))

        # Deploy healthy, recently fed Warriors. Keep Farmers in the Village.
        for villager in villagers:
            if id(villager) in assigned:
                continue

            role = getattr(villager, "role", "")
            hunger = getattr(villager, "steps_since_meal", 0)

            if role == "Warrior" and hunger <= 2 and dragon_hp > 0:
                self._assign(environment, villager, group_ids, "cave")
            else:
                self._assign(environment, villager, group_ids, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Return with enough time to reach the Village and eat before
            # starvation makes the villager unable to deal damage.
            if hunger >= 4 or hp <= 1:
                self._assign(environment, villager, group_ids, "village")
            else:
                self._assign(environment, villager, group_ids, "attack")
```