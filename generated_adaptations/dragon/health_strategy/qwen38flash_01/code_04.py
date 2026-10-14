from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat_budget = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors in village go to cave immediately (they will attack next step)
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining_farmers = list(farmers)
        MIN_FARMING = 2  # always keep at least 2 farmers farming for wheat production

        # Early game: spawn up to 2 farmers to grow economy
        if self.spawned_farmers < 2:
            while self.spawned_farmers < 2 and len(remaining_farmers) - 2 >= MIN_FARMING and wheat_budget >= 10:
                environment.assign_group(remaining_farmers[0], "spawn farmer")
                environment.assign_group(remaining_farmers[1], "spawn farmer")
                remaining_farmers = remaining_farmers[2:]
                wheat_budget -= 10
                self.spawned_farmers += 1

        # Aggressively spawn warriors to maintain a continuous attack pipeline
        # Use pairs of farmers + 12 wheat per warrior
        # Must leave MIN_FARMING farmers still farming
        while len(remaining_farmers) - 2 >= MIN_FARMING and wheat_budget >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            remaining_farmers = remaining_farmers[2:]
            wheat_budget -= 12

        # All remaining farmers farm to generate wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors deal 3 damage — always attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should never be in the cave; send them back
                environment.assign_group(c, "village")