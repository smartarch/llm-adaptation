from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MIN_VILLAGE_FARMERS = 1    # farmers that always stay on the farm

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

        # 2) Spawn warriors from village farmers, but never take the last
        #    reserved farmer, so the village always keeps a worker.
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2 + self.MIN_VILLAGE_FARMERS
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Keep a minimum number of farmers on the farm.
        reserve = min(self.MIN_VILLAGE_FARMERS, len(available))
        for f in available[:reserve]:
            environment.assign_group(f, "farm")

        # 4) All remaining farmers join the attack (1 damage each per step).
        for f in available[reserve:]:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        # Everyone in the cave attacks: retaliation is per step, not per attacker.
        for c in components:
            environment.assign_group(c, "attack")