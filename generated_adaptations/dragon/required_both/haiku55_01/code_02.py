from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Village: feed hungry villagers first, spawn reinforcements (warriors preferred)
      with remaining wheat, send well-fed warriors to the Cave, farm with the rest.
    - Cave: attack with well-fed warriors, send hungry villagers and farmers back
      to the Village, keep the rest in the Cave.
    """

    HUNGER_EAT_THRESHOLD = 3    # village: eat when steps_since_meal >= 3
    HUNGER_RETURN_THRESHOLD = 3  # cave: go back to village when steps_since_meal >= 3
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _hunger(self, c):
        return getattr(c, "steps_since_meal", 0)

    def _role(self, c):
        return getattr(c, "role", "")

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = getattr(environment.farm, "wheat", 0)

        # 1. Feed hungry villagers first (each meal costs 1 wheat).
        hungry = [c for c in comps if self._hunger(c) >= self.HUNGER_EAT_THRESHOLD]
        eating_ids = set(id(c) for c in hungry)
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_after_meals = wheat - len(hungry)

        remaining = [c for c in comps if id(c) not in eating_ids]
        farmers = [c for c in remaining if self._role(c) == "Farmer"]
        warriors = [c for c in remaining if self._role(c) == "Warrior"]

        spawning_ids = set()

        # 2. Spawn with leftover wheat (spawners are farmers, to keep warriors free).
        if len(farmers) >= 2 and wheat_after_meals >= self.WARRIOR_COST:
            spawners = farmers[:2]
            for c in spawners:
                environment.assign_group(c, "spawn warrior")
                spawning_ids.add(id(c))
            wheat_after_meals -= self.WARRIOR_COST
        elif len(farmers) >= 2 and wheat_after_meals >= self.FARMER_COST:
            spawners = farmers[:2]
            for c in spawners:
                environment.assign_group(c, "spawn farmer")
                spawning_ids.add(id(c))
            wheat_after_meals -= self.FARMER_COST

        # 3. Send well-fed warriors to the Cave.
        for c in warriors:
            if self._hunger(c) < self.HUNGER_EAT_THRESHOLD:
                environment.assign_group(c, "cave")
                spawning_ids.add(id(c))  # mark as assigned

        # 4. Everyone else (farmers not spawning) farms; hungry warriors that
        #    were not eating (should not happen) go to farm too.
        for c in remaining:
            if id(c) in spawning_ids:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hunger = self._hunger(c)
            role = self._role(c)

            if role == "Farmer":
                # Farmers must stay in the Village.
                environment.assign_group(c, "village")
            elif hunger >= self.HUNGER_RETURN_THRESHOLD:
                # Hungry warrior: go back to eat before it starves.
                environment.assign_group(c, "village")
            else:
                # Healthy warrior: attack the Dragon.
                environment.assign_group(c, "attack")