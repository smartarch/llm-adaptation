import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors immediately go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = environment.farm.wheat
        assigned = set()

        # Phase 1: Grow farmer base in first few turns (need 2 new farmers)
        # Phase 2: Spawn warriors every single turn possible
        # We only need 3 farmers total to spawn (2 in spawn group + 1 farming minimum)

        remaining_farmers = list(farmers)

        # Priority: if we still need 2 farmers spawned AND have enough, do farmer spawns early
        if self.spawned_farmers < 2 and step <= 6 and wheat >= 10 and len(remaining_farmers) >= 3:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 10
            self.spawned_farmers += 1
            remaining_farmers = remaining_farmers[2:]

        # Spawn warriors as aggressively as possible
        # Need 2 farmers in spawn group + 12 wheat per warrior
        # Keep at least 1 farmer farming so we don't stall economy
        while len(remaining_farmers) >= 3 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 12
            self.spawned_warriors += 1
            remaining_farmers = remaining_farmers[2:]

        # If we have excess wheat and many farmers, spawn more warriors
        # (can do multiple spawns per turn if wheat >= 24 and enough farmers)
        # The while loop above already handles this.

        # All unassigned farmers go farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave attack every turn unconditionally
        # Never send warriors back to village - even at 1 HP they deal 3 damage
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Any non-warrior (farmer) that ended up in cave goes back to village
                environment.assign_group(c, "village")