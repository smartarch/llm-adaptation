import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn = 0
        self.spawned_w = 0
        self.spawned_f = 0

    def assign_in_village(self, components, environment, group_ids, step):
        self.turn += 1
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # --- EARLY GAME: Build farmer pool using warriors as spawn fodder ---
        # We need to grow from 2 farmers to 3+ so we can both farm AND spawn.
        # Use 1 warrior + 1 farmer to spawn a farmer (costs 10w).
        # Keep the other warrior going to cave for early attacks.

        if wheat >= 10 and len(warriors) >= 1 and len(farmers) >= 1 and self.spawned_f < 2:
            # Use 1 warrior + 1 farmer as spawn fodder for a farmer
            environment.assign_group(warriors[0], "spawn farmer")
            environment.assign_group(farmers[0], "spawn farmer")
            self.spawned_f += 1

            # Send remaining warriors to cave
            for w in warriors[1:]:
                environment.assign_group(w, "cave")

            # Remaining farmers farm
            for f in farmers[1:]:
                environment.assign_group(f, "farm")
            return

        # --- NORMAL GAME: All warriors to cave, spawn warriors every turn ---
        # Send ALL warriors to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Try to spawn warriors: need 2 farmers for spawn group, 
        # and at least 1 farmer left to farm (so need 3+ farmers total)
        remaining_farmers = list(farmers)

        # Spawn as many warriors as possible while keeping >= 1 farmer farming
        while len(remaining_farmers) >= 3 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            wheat -= 12
            self.spawned_w += 1
            remaining_farmers = remaining_farmers[2:]

        # If we still have surplus farmers and wheat, try to also spawn a farmer
        # (but only if we'll still have >= 1 farming after)
        while len(remaining_farmers) >= 3 and wheat >= 10 and self.spawned_w < 4:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            wheat -= 10
            self.spawned_f += 1
            remaining_farmers = remaining_farmers[2:]
            break  # only one farmer spawn per turn

        # All remaining farmers farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave attack every single turn - never retreat
        # Any non-warrior (farmer) in cave goes back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")