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

        # Spawn warriors aggressively: every turn we have 4+ farmers and 12+ wheat
        # Use exactly 2 farmers per spawn, keep at least 2 farming if possible
        remaining_farmers = list(farmers)

        while len(remaining_farmers) >= 4 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 12
            self.spawned_warriors += 1
            remaining_farmers = remaining_farmers[2:]

        # Spawn farmers: only if we've already got at least 2 warrior spawns
        # and still have surplus farmers
        remaining_farmers = [f for f in farmers if id(f) not in assigned]

        while len(remaining_farmers) >= 4 and wheat >= 10 and self.spawned_warriors >= 2:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 10
            self.spawned_farmers += 1
            remaining_farmers = remaining_farmers[2:]

        # All unassigned farmers go farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave attack the dragon every turn - never retreat
        # Non-warriors (if any) go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")