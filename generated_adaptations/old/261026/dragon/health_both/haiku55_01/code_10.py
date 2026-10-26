from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    TARGET_FARMERS = 4         # farmers to keep for wheat and spawning
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MAX_FARMER_PAIRS = 1       # farmer spawn pairs per step
    FARM_RESERVE = 2           # farmers that always stay in the village

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0
        self.cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        total_warriors = len(warriors) + self.cave_warriors
        total_farmers = len(farmers) + self.cave_farmers

        available = list(farmers)
        budget = wheat

        # 2) Spawn warriors first (main damage source).
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1
            warrior_pairs += 1

        # 3) Replenish farmers when the population drops.
        farmer_pairs = 0
        while (farmer_pairs < self.MAX_FARMER_PAIRS
               and budget >= 10
               and len(available) >= 2
               and total_farmers < self.TARGET_FARMERS):
            environment.assign_group(available.pop(0), "spawn farmer")
            environment.assign_group(available.pop(0), "spawn farmer")
            budget -= 10
            total_farmers += 1
            farmer_pairs += 1

        # 4) Decide whether farmers must fight. Only when no warriors are alive.
        no_warriors = (total_warriors == 0)

        if dragon_hp > 0 and no_warriors and len(available) > self.FARM_RESERVE:
            # Send the surplus farmers to attack; keep a reserve on the farm.
            attackers = available[self.FARM_RESERVE:]
            farmers_on_farm = available[:self.FARM_RESERVE]
            for f in attackers:
                environment.assign_group(f, "cave")
            for f in farmers_on_farm:
                environment.assign_group(f, "farm")
        else:
            for f in available:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        for w in warriors:
            environment.assign_group(w, "attack")

        for f in farmers:
            if warriors:
                # Warriors are fighting: farmers go home to survive and farm.
                environment.assign_group(f, "village")
            else:
                # No warriors left: farmers keep the damage going.
                environment.assign_group(f, "attack")