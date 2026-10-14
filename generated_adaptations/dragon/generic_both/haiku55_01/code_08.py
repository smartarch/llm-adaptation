import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy-first, then army-focused strategy.
    - Early on, spawn farmers (cheap, and each one adds 5 wheat/step) until a
      target farmer count is reached.
    - Then spend wheat on warriors, keeping about half of the farmers farming.
    - All warriors go to the Cave and attack every step.
    - Farmers join the attack only in the final push (Dragon HP <= 15).
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    FARMER_TARGET = 8           # grow the economy to this many farmers first
    MIN_FARMING = 2             # always keep at least this many farmers on the farm
    ECONOMY_PHASE_STEPS = 12    # after this step, prioritise warriors
    FINAL_PUSH_HP = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reserve farmers that keep producing wheat.
        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        economy_phase = (len(farmers) < self.FARMER_TARGET
                         and step < self.ECONOMY_PHASE_STEPS)

        if economy_phase:
            # Grow the farmer population while wheat allows.
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Convert wheat into warriors, but keep about half the farmers farming.
            keep = max(self.MIN_FARMING, len(farmers) // 2)
            extra_farming = max(0, keep - reserve)
            farming.extend(available[:extra_farming])
            available = available[extra_farming:]

            while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
                spawn_warrior.extend(available[:2])
                available = available[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        # Anyone left over keeps farming.
        farming.extend(available)

        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        final_push = dragon_hp <= self.FINAL_PUSH_HP

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif final_push:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")