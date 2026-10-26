import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.target_extra_warriors = 4  # spawn 4 extra warriors for a strong assault
        self.target_extra_farmers = 2   # spawn 2 extra farmers for economy

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # --- All warriors go to the Cave ---
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Farmers handle spawning and farming ---
        # We must always keep at least 2 farmers farming to sustain the economy.
        min_farming = 2

        idx = 0  # pointer into the farmers list

        need_more_warriors = self.warriors_spawned < self.target_extra_warriors
        need_more_farmers = self.farmers_spawned < self.target_extra_farmers

        # Priority 1: Spawn a Warrior (most impactful for killing the Dragon)
        if need_more_warriors and (len(farmers) - idx) >= 4 and wheat >= 12:
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2
            self.warriors_spawned += 1

        # Priority 2: Spawn a Farmer (for long-term economy, only 2 needed)
        need_more_warriors = self.warriors_spawned < self.target_extra_warriors
        if need_more_farmers and (len(farmers) - idx) >= 4 and wheat >= 10:
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
            self.farmers_spawned += 1

        # Priority 3: All remaining farmers go to the farm
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors stay in the Cave and attack the Dragon every turn
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be stuck in the Cave — send them back
                environment.assign_group(c, "village")