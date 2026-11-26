from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers before they starve, send healthy warriors to
        the Cave once a launch group is ready, spawn new warriors from pairs of
        non-warrior villagers whenever wheat allows, and keep everyone else
        farming. Farmers never go to the Cave.
      - Cave: warriors attack every step while they are fed and healthy, so the
        Dragon never gets a step to regenerate. Hungry or badly wounded warriors
        return to the Village. Any farmer in the Cave goes back to farm.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat early, well before the 6-step limit
    RETREAT_THRESHOLD = 4       # leave the Cave when hunger reaches this
    LAUNCH_SIZE = 3             # ready warriors needed to send a group
    MIN_WARRIOR_HP_CAVE = 2     # warriors below this retreat
    MIN_WARRIOR_HP_LAUNCH = 3   # warriors below this stay home
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = {}

        def assign(c, group):
            environment.assign_group(c, group)
            assigned[id(c)] = group

        wheat = environment.farm.wheat

        # 1. Eating: feed villagers that are getting hungry (costs 1 wheat each).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Launching: healthy, recently fed warriors go to the Cave as a group.
        ready_warriors = [
            c for c in remaining
            if c.role == "Warrior"
            and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
            and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE
        ]
        if environment.dragon.hp > 0 and len(ready_warriors) >= self.LAUNCH_SIZE:
            for c in ready_warriors:
                assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 3. Spawning: pairs of non-warrior villagers spawn a new warrior when
        #    wheat covers the cost plus one meal for every villager.
        reserve = len(components)
        if environment.dragon.hp > 0 and wheat >= self.WARRIOR_COST + reserve:
            spawn_pool = [c for c in remaining if c.role == "Farmer"]
            if len(spawn_pool) < 2:
                spawn_pool += [c for c in remaining if c.role == "Warrior" and c not in spawn_pool]
            if len(spawn_pool) >= 2:
                for c in spawn_pool[:2]:
                    assign(c, "spawn warrior")

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Everyone else farms (farmers never go to the Cave).
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers are not sent to fight; return them to farm.
                environment.assign_group(c, "village")
            elif environment.dragon.hp <= 0:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal >= self.RETREAT_THRESHOLD or c.hp < self.MIN_WARRIOR_HP_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")