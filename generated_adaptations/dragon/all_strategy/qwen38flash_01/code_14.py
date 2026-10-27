from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._last_send_step = -10

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # Priority: eat if ssm >= 4, otherwise stagger departures every 3 steps
        sorted_warriors = sorted(warriors, key=lambda w: w.steps_since_meal)
        sent_one = False
        for w in sorted_warriors:
            if w.steps_since_meal >= 4:
                # Must eat now (ssm=5 next step = starvation)
                environment.assign_group(w, "eat")
            elif not sent_one and w.steps_since_meal <= 1 and (step - self._last_send_step >= 3):
                # Fresh warrior and it's their turn: send to cave
                environment.assign_group(w, "cave")
                self._last_send_step = step
                sent_one = True
            else:
                # Not their turn or not fresh: eat to keep ssm low
                environment.assign_group(w, "eat")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        avail_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        idx = 0
        n = len(avail_farmers)

        # Spawn warriors aggressively (need 2 per spawn, 12 wheat each)
        # Keep spawning to replace dead warriors and build DPS
        while (n - idx >= 2) and wheat >= 12:
            environment.assign_group(avail_farmers[idx], "spawn warrior")
            environment.assign_group(avail_farmers[idx + 1], "spawn warrior")
            self._spawned_warriors += 1
            wheat -= 12
            idx += 2
            if self._spawned_warriors >= 5:
                break

        # Spawn farmers (need 2 per spawn, 10 wheat each)
        while (n - idx >= 2) and wheat >= 10:
            environment.assign_group(avail_farmers[idx], "spawn farmer")
            environment.assign_group(avail_farmers[idx + 1], "spawn farmer")
            self._spawned_farmers += 1
            wheat -= 10
            idx += 2
            if self._spawned_farmers >= 3:
                break

        # Remaining farmers farm for wheat production
        for f in avail_farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be in cave
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: attack while safe, leave at ssm >= 4
        # At ssm=4 leaving cave → arrive village ssm=5 → eat next step (no HP loss)
        # At ssm=3 attacking: ssm becomes 4, next step must leave
        for w in warriors:
            if w.steps_since_meal >= 4:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")