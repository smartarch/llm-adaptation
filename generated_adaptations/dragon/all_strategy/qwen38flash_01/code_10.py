from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._last_cave_departure = -10

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # ssm >= 4: must eat now (next step would be ssm=5 = starvation trigger)
        # ssm < 4 and time to stagger: go to cave
        # ssm < 4 and not yet time: eat to keep ssm=0 for when turn comes
        sorted_warriors = sorted(warriors, key=lambda w: w.steps_since_meal)
        sent_one = False
        for w in sorted_warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "eat")
            elif not sent_one and (step - self._last_cave_departure >= 3):
                environment.assign_group(w, "cave")
                self._last_cave_departure = step
                sent_one = True
            else:
                environment.assign_group(w, "eat")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        avail_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # Allocate available farmers: spawn warriors > spawn farmers > farm
        idx = 0
        n = len(avail_farmers)

        # Must keep at least 1 farmer farming if any remain after spawning
        min_farming = 1

        # Spawn warriors aggressively
        while (n - idx >= 2 + min_farming) and wheat >= 12:
            environment.assign_group(avail_farmers[idx], "spawn warrior")
            environment.assign_group(avail_farmers[idx + 1], "spawn warrior")
            self._spawned_warriors += 1
            wheat -= 12
            idx += 2
            # Stop spawning warriors if we have plenty (4-5 is good)
            if self._spawned_warriors >= 4:
                break

        # Spawn farmers (need at least 2 for requirement)
        while (n - idx >= 2 + min_farming) and wheat >= 10:
            environment.assign_group(avail_farmers[idx], "spawn farmer")
            environment.assign_group(avail_farmers[idx + 1], "spawn farmer")
            self._spawned_farmers += 1
            wheat -= 10
            idx += 2
            if self._spawned_farmers >= 2:
                break

        # Remaining farmers farm
        for f in avail_farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers shouldn't be in cave
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: attack while safe, leave at ssm >= 4
        # At ssm=4 in cave, next step would be ssm=5 (violation since can't eat in cave)
        # So leave at ssm=4, arrive village at ssm=5, eat there.
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")