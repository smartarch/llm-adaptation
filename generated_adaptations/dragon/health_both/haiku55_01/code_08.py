from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10        # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 2       # warrior spawn pairs per step
    MIN_VILLAGE_FARMERS = 1     # farmers that always stay in the village

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0
        self.cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        total_warriors = len(warriors) + self.cave_warriors
        available = list(farmers)
        budget = wheat

        # 2) Spawn warriors from village farmers (up to MAX_WARRIOR_PAIRS per step).
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Keep a minimum number of farmers in the village (farming).
        reserve = min(self.MIN_VILLAGE_FARMERS, len(available))
        farm_group = available[:reserve]
        attack_group = available[reserve:]

        for f in farm_group:
            environment.assign_group(f, "farm")

        # 4) All remaining farmers join the attack: each adds 1 damage per step.
        for f in attack_group:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        # Everyone in the cave attacks: the Dragon's counterattack is per step,
        # so more attackers means more damage for the same retaliation risk.
        for c in components:
            environment.assign_group(c, "attack")