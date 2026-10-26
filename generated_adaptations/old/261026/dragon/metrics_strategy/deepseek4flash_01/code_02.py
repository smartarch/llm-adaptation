from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All Warriors go to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Fallback: if no Warrior has been spawned and it's late, send one Farmer
        # to the Cave to ensure we attack before step 15. Only do this if we
        # cannot spawn a Warrior this step.
        if self.spawned_warriors == 0 and step >= 10 and farmers:
            if not (len(farmers) >= 2 and environment.farm.wheat >= 12):
                environment.assign_group(farmers[0], "cave")
                farmers = farmers[1:]

        if not farmers:
            return

        n = len(farmers)
        wheat = environment.farm.wheat
        farmer_pairs = 0
        warrior_pairs = 0

        # 1. Spawn first Warrior if we have none and can afford it.
        if self.spawned_warriors == 0 and n >= 2 and wheat >= 12:
            warrior_pairs += 1
            n -= 2
            wheat -= 12
            self.spawned_warriors += 1

        # 2. Spawn first Farmer if we have none and can afford it.
        if self.spawned_farmers == 0 and n >= 2 and wheat >= 10:
            farmer_pairs += 1
            n -= 2
            wheat -= 10
            self.spawned_farmers += 1

        # 3. Spawn second Farmer if still needed and conditions are favorable.
        if self.spawned_farmers < 2 and n >= 2 and wheat >= 10:
            if wheat < 12 or step >= 10 or (n >= 4 and wheat >= 22):
                farmer_pairs += 1
                n -= 2
                wheat -= 10
                self.spawned_farmers += 1

        # 4. Spawn as many Warriors as possible with remaining farmers and wheat.
        max_warrior_pairs = min(n // 2, wheat // 12)
        if max_warrior_pairs > 0:
            warrior_pairs += max_warrior_pairs
            n -= 2 * max_warrior_pairs
            wheat -= 12 * max_warrior_pairs
            self.spawned_warriors += max_warrior_pairs

        # Perform the assignments.
        idx = 0
        for _ in range(farmer_pairs):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2
        for _ in range(warrior_pairs):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2
        for f in farmers[idx:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        if warriors:
            # All Warriors attack, Farmers go back to the Village.
            for w in warriors:
                environment.assign_group(w, "attack")
            for f in farmers:
                environment.assign_group(f, "village")
        else:
            # No Warriors in the Cave. If there are Farmers, send most back to
            # the Village, but keep one attacking early to satisfy the early-attack
            # requirement (e.g., if a Farmer was sent as a fallback).
            if farmers:
                if step < 15:
                    environment.assign_group(farmers[0], "attack")
                    for f in farmers[1:]:
                        environment.assign_group(f, "village")
                else:
                    for f in farmers:
                        environment.assign_group(f, "village")