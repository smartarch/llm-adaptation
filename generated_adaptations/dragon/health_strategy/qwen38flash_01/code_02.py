from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        wheat = environment.farm.wheat

        # All warriors in village go to cave (to eventually attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Use remaining farmers for spawning or farming
        remaining_farmers = list(farmers)

        # Priority 1: Spawn warriors (deal 3 dmg, crucial for killing dragon)
        # Need pairs of farmers and 12 wheat per warrior
        while len(remaining_farmers) >= 2 and self.spawned_warriors < 2:
            # Check actual wheat available (use observed value; be conservative)
            if environment.farm.wheat >= 12 * (self.spawned_warriors - self.spawned_warriors + 1):
                environment.assign_group(remaining_farmers[0], "spawn warrior")
                environment.assign_group(remaining_farmers[1], "spawn warrior")
                remaining_farmers = remaining_farmers[2:]
                self.spawned_warriors += 1
            else:
                break

        # Priority 2: Spawn farmers (to grow economy)
        while len(remaining_farmers) >= 2 and self.spawned_farmers < 2:
            if environment.farm.wheat >= 10:
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                self.spawned_farmers += 1
            else:
                break

        # All remaining farmers stay in village and farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon - deal 3 damage per attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in cave - send them back to village
                environment.assign_group(c, "village")