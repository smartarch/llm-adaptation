from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers that have not eaten for >= 2 steps go to the Village 'eat' group
      (eating in the Village is the only way to avoid starvation).
    - Early in the game, two ready warriors are used to spawn a new warrior when
      there is enough wheat (keeping a reserve for meals).
    - Remaining ready warriors go to the Cave to attack (highest damage dealers).
    - Remaining ready farmers stay on the farm to produce wheat.
    - In the Cave, villagers that are fed recently (steps_since_meal <= 2) attack;
      villagers with steps_since_meal >= 3 return to the Village to eat before
      they starve.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat as soon as hunger is noticed in the village
    RETURN_THRESHOLD_CAVE = 3   # go back to eat when hunger reaches this in the cave
    SPAWN_WINDOW_STEPS = 8      # spawn early while the dragon is still at full strength

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat = []
        ready = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                eat.append(c)
            else:
                ready.append(c)

        # Wheat needed this step for meals (1 wheat per eating villager)
        wheat_available = wheat - len(eat)

        ready_warriors = [c for c in ready if c.role == "Warrior"]
        ready_farmers = [c for c in ready if c.role == "Farmer"]

        spawn_warriors = []
        if (step <= self.SPAWN_WINDOW_STEPS
                and wheat_available >= 12
                and len(ready_warriors) >= 2):
            spawn_warriors = ready_warriors[:2]

        spawn_set = set(id(c) for c in spawn_warriors)
        cave_group = []
        farm_group = []
        for c in ready:
            if id(c) in spawn_set:
                continue
            if c.role == "Warrior":
                cave_group.append(c)
            else:
                farm_group.append(c)

        for c in components:
            if c in eat or any(c is e for e in eat):
                environment.assign_group(c, "eat")
            elif any(c is s for s in spawn_warriors):
                environment.assign_group(c, "spawn warrior")
            elif any(c is g for g in cave_group):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE:
                environment.assign_group(c, "village")
            elif c.steps_since_meal <= 2 and c.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")