from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._last_departure_step = -10  # step when last warrior was sent from village to cave

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # Must eat if ssm >= 5 (ssm=6 means starvation)
        must_eat = [w for w in warriors if w.steps_since_meal >= 5]
        can_act = [w for w in warriors if w.steps_since_meal < 5]

        for w in must_eat:
            environment.assign_group(w, "eat")

        # Stagger: only send one warrior to cave every 3 steps for perfect coverage
        if can_act:
            can_act_sorted = sorted(can_act, key=lambda w: w.steps_since_meal)
            if step - self._last_departure_step >= 3:
                # Send the least hungry warrior to cave
                environment.assign_group(can_act_sorted[0], "cave")
                self._last_departure_step = step
                # Others wait (eat to reset ssm, creating proper stagger for next time)
                for w in can_act_sorted[1:]:
                    environment.assign_group(w, "eat")
            else:
                # Not time yet, have them eat to reset ssm and wait
                for w in can_act_sorted:
                    environment.assign_group(w, "eat")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 5]
        available_farmers = [f for f in farmers if f.steps_since_meal < 5]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # Allocate available farmers: spawn warriors first, then farmers, rest farm
        idx = 0
        n = len(available_farmers)
        min_farming = 1  # Keep at least 1 farmer farming

        # Spawn warriors aggressively (need pairs in group, costs 12 wheat each)
        # Target many warriors for DPS
        target_warriors = 5
        while (self._spawned_warriors < target_warriors) and (n - idx >= 2 + min_farming) and wheat >= 12:
            environment.assign_group(available_farmers[idx], "spawn warrior")
            environment.assign_group(available_farmers[idx + 1], "spawn warrior")
            self._spawned_warriors += 1
            wheat -= 12
            idx += 2

        # Spawn farmers (target 3 spawned to keep farming population)
        target_farmers = 3
        while (self._spawned_farmers < target_farmers) and (n - idx >= 2 + min_farming) and wheat >= 10:
            environment.assign_group(available_farmers[idx], "spawn farmer")
            environment.assign_group(available_farmers[idx + 1], "spawn farmer")
            self._spawned_farmers += 1
            wheat -= 10
            idx += 2

        # Remaining farmers farm
        for f in available_farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers shouldn't be in cave
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: attack unless about to starve
        # ssm >= 5: must return. Transit takes 1 step, arrive village ssm=6 (lose 1HP), then eat.
        # ssm < 5: safe to keep attacking.
        for w in warriors:
            if w.steps_since_meal >= 5:
                environment.assign_group(w, "village")
            else:
                environment.assign_group(w, "attack")