The strategy is adaptive and resource-aware. In the Village, all warriors are immediately sent to the Cave. Farmers are used to spawn new villagers only when enough wheat is available: first we guarantee a few new farmers, then a few new warriors, then grow the farmer economy, and finally spawn more warriors for damage. Any remaining farmers work on the farm. In the Cave, all warriors attack the Dragon, while any farmers that end up there are sent back to the Village so they can satisfy the requirement to stay in the Village. Spawn counts are tracked with minimum and maximum caps, ensuring that at least a few new farmers and warriors are created without wasting all wheat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawns = 0
        self.warrior_spawns = 0

    def _assign(self, environment, component, group_id, group_ids):
        if group_id in group_ids:
            environment.assign_group(component, group_id)
        else:
            # Fallback to a valid group if the preferred one is unavailable.
            environment.assign_group(component, group_ids[0])

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All warriors go to the Cave immediately.
        for w in warriors:
            self._assign(environment, w, "cave", group_ids)

        wheat = getattr(environment.farm, "wheat", 0)
        budget = wheat

        min_farmer_spawns = 3
        min_warrior_spawns = 3
        max_farmer_spawns = 8
        max_warrior_spawns = 15
        target_farmers = 10

        spawn_farmer_components = []
        spawn_warrior_components = []

        def available_farmers():
            return [
                f for f in farmers
                if f not in spawn_farmer_components and f not in spawn_warrior_components
            ]

        def reserve_for_spawn(group_list, cost):
            nonlocal budget
            if len(available_farmers()) >= 2 and budget >= cost:
                chosen = available_farmers()[:2]
                group_list.extend(chosen)
                budget -= cost
                return True
            return False

        # Ensure at least a few new farmers.
        if self.farmer_spawns < min_farmer_spawns:
            if reserve_for_spawn(spawn_farmer_components, 10):
                self.farmer_spawns += 1

        # Ensure at least a few new warriors.
        if self.warrior_spawns < min_warrior_spawns:
            if reserve_for_spawn(spawn_warrior_components, 12):
                self.warrior_spawns += 1

        # Grow the farmer economy if needed.
        if (len(farmers) < target_farmers or self.farmer_spawns < min_farmer_spawns) and self.farmer_spawns < max_farmer_spawns:
            if reserve_for_spawn(spawn_farmer_components, 10):
                self.farmer_spawns += 1

        # Spawn more warriors for damage when resources allow.
        if self.warrior_spawns < max_warrior_spawns:
            if reserve_for_spawn(spawn_warrior_components, 12):
                self.warrior_spawns += 1

        # Assign chosen farmers to their spawn groups.
        for f in spawn_farmer_components:
            self._assign(environment, f, "spawn farmer", group_ids)
        for f in spawn_warrior_components:
            self._assign(environment, f, "spawn warrior", group_ids)

        # Every other farmer works on the farm.
        for f in farmers:
            if f not in spawn_farmer_components and f not in spawn_warrior_components:
                self._assign(environment, f, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # All warriors attack the Dragon.
                self._assign(environment, c, "attack", group_ids)
            else:
                # Farmers (and any other roles) should return to the Village.
                self._assign(environment, c, "village", group_ids)
```