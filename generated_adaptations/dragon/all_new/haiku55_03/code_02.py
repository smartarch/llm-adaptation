from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers that are getting hungry, spawn warriors while
        wheat allows (before the attack is launched), send a group of healthy
        warriors to the Cave once enough are available, and keep everyone
        else farming.
      - Cave: retreat starving or badly wounded villagers to the Village to
        eat/recover, and make everyone else attack the Dragon every step so
        its regeneration never kicks in.
    """

    EAT_THRESHOLD = 3       # eat before reaching the 6-step starvation limit
    RETREAT_THRESHOLD = 3   # leave the Cave before starving
    LAUNCH_SIZE = 4         # healthy warriors needed to launch the attack
    LATE_LAUNCH_STEP = 18   # fallback: attack regardless after this step
    MIN_FARM_HP_FOR_CAVE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_launched = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        # 1. Feeding: villagers that are getting hungry eat (costs 1 wheat each).
        eat_budget = wheat
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if c.steps_since_meal >= self.EAT_THRESHOLD and eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Decide whether to launch the attack.
        healthy_warriors = [
            c for c in remaining
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.EAT_THRESHOLD
        ]
        if (len(healthy_warriors) >= self.LAUNCH_SIZE) or (step >= self.LATE_LAUNCH_STEP and healthy_warriors):
            self.attack_launched = True

        # Send warriors to the Cave when launching.
        if self.attack_launched:
            for c in healthy_warriors:
                assign(c, "cave")
            # Healthy farmers may also join if the Dragon is still alive and
            # they have enough HP to survive retaliation.
            for c in remaining:
                if id(c) in assigned:
                    continue
                if c.role == "Farmer" and c.hp > self.MIN_FARM_HP_FOR_CAVE + 1 and \
                        c.steps_since_meal < self.EAT_THRESHOLD and environment.dragon.hp > 0 and \
                        len(healthy_warriors) < self.LAUNCH_SIZE:
                    assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 3. Spawning: before the attack, grow the warrior force.
        if not self.attack_launched and environment.farm.wheat >= 12 + eat_budget * 0:
            spawn_candidates = [c for c in remaining if c.steps_since_meal < self.EAT_THRESHOLD]
            if len(spawn_candidates) >= 2 and environment.farm.wheat - (len(components) - len(remaining)) >= 12:
                for c in spawn_candidates[:2]:
                    assign(c, "spawn warrior")

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Everyone else farms.
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETREAT_THRESHOLD:
                # Starving: go back to eat, they cannot deal damage anyway.
                environment.assign_group(c, "village")
            elif c.role == "Farmer" and c.hp < self.MIN_FARM_HP_FOR_CAVE:
                # Too wounded to survive another retaliation.
                environment.assign_group(c, "village")
            elif environment.dragon.hp <= 0:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "attack")