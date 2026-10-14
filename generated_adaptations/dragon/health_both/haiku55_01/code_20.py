from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    MAX_WARRIOR_SPAWN_ORDERS = 8   # total warrior spawn pairs ever issued
    MAX_WARRIOR_PAIRS = 2          # warrior spawn pairs per step
    MIN_FARMERS_TO_SPAWN = 3       # keep at least one farmer free to attack

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior in the village goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn warriors from farmers, keeping at least one farmer free.
        available = list(farmers)
        budget = wheat
        pairs = 0
        while (pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= self.MIN_FARMERS_TO_SPAWN
               and self.warrior_spawn_orders < self.MAX_WARRIOR_SPAWN_ORDERS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            pairs += 1
            self.warrior_spawn_orders += 1

        # 3) Every remaining farmer attacks: 1 damage each per step.
        for f in available:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Everyone in the cave attacks. Retaliation is per step, not per attacker,
        # so extra attackers add damage without adding risk.
        for c in components:
            environment.assign_group(c, "attack")