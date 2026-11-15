from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # Must eat if ssm >= 4 (going to cave would put them at ssm >= 5 in cave
        # next step, which violates the eat constraint).
        # Otherwise send to cave to attack.
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        full_farmers = [f for f in farmers if f.steps_since_meal < 4]

        # Hungry farmers must eat
        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # Allocate full_farmers to: spawn warrior > spawn farmer > farm
        idx = 0
        n = len(full_farmers)

        # Need at least 1 farmer farming to produce wheat (if we have any)
        min_farming = 1

        # Spawn warriors aggressively (target up to 5 spawned)
        while (self._spawned_warriors < 5) and (n - idx >= 2 + min_farming) and wheat >= 12:
            environment.assign_group(full_farmers[idx], "spawn warrior")
            environment.assign_group(full_farmers[idx + 1], "spawn warrior")
            self._spawned_warriors += 1
            wheat -= 12
            idx += 2

        # Spawn farmers (target 2-3 spawned)
        while (self._spawned_farmers < 3) and (n - idx >= 2 + min_farming) and wheat >= 10:
            environment.assign_group(full_farmers[idx], "spawn farmer")
            environment.assign_group(full_farmers[idx + 1], "spawn farmer")
            self._spawned_farmers += 1
            wheat -= 10
            idx += 2

        # Remaining farmers farm
        for f in full_farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should not be in cave; send back to village
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: attack unless ssm >= 4 (they'd reach ssm=5 in cave next step
        # if they attack at ssm=4, violating the eat constraint).
        # At ssm >= 4, return to village (arrive at ssm=5, eat next step).
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")