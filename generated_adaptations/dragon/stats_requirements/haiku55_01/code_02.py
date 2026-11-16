import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Village: feed anyone with steps_since_meal >= 2; spawn 2 warriors and then
      1 farmer when wheat allows (spawners are taken from non-eating villagers,
      preferring farmers); warriors that are fed and not spawning go to the Cave;
      farmers keep farming.
    - Cave: warriors with steps_since_meal < 3 attack; hungrier warriors and all
      farmers return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat when this many steps have passed without a meal
    CAVE_ATTACK_LIMIT = 3       # warriors in the cave attack only if steps_since_meal < this
    WARRIOR_SPAWN_TARGET = 2
    FARMER_SPAWN_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (eating consumes 1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        remaining = [c for c in components if c not in assigned]

        # Helper: pick spawners, preferring farmers so warriors stay available.
        def pick_spawners(n):
            farmers = [c for c in remaining if c.role == "Farmer" and c not in assigned]
            others = [c for c in remaining if c.role != "Farmer" and c not in assigned]
            return (farmers + others)[:n]

        # 2) Spawning: at most one spawn group per step.
        spawned_this_step = False
        if self.warriors_spawned < self.WARRIOR_SPAWN_TARGET and budget >= self.WARRIOR_COST:
            spawners = pick_spawners(2)
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn warrior")
                    assigned.add(c)
                budget -= self.WARRIOR_COST
                self.warriors_spawned += 1
                spawned_this_step = True

        if (not spawned_this_step
                and self.warriors_spawned >= self.WARRIOR_SPAWN_TARGET
                and self.farmers_spawned < self.FARMER_SPAWN_TARGET
                and budget >= self.FARMER_COST):
            spawners = pick_spawners(2)
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn farmer")
                    assigned.add(c)
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Everyone else: fed warriors go to the Cave, farmers keep farming.
        for c in components:
            if c in assigned:
                continue
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_ATTACK_LIMIT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")