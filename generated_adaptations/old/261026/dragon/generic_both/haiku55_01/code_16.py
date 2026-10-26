import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Short economy opening, then a batch strike.
    - Steps 0-2: all farmers farm to build wheat; warriors wait in the Cave.
    - Afterwards: two farmers always farm. If the farmer count is below 4,
      pairs spawn farmers (10 wheat) to rebuild income; otherwise pairs
      spawn warriors (12 wheat).
    - Strike (one-way switch) when >=4 warriors are in the Cave or step >= 10.
      Then all warriors in the Cave attack every step.
    - Farmers never enter the Cave.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    OPENING_STEPS = 3
    MIN_FARMING = 2
    MIN_FARMERS = 4
    STRIKE_WARRIORS = 4
    STRIKE_STEP = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strike = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always head to the Cave (they wait there until the strike).
        for w in warriors:
            environment.assign_group(w, "cave")

        # Opening: everyone farms to build wheat.
        if step < self.OPENING_STEPS:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_farmer = []
        spawn_warrior = []

        # Rebuild the farmer economy if too few farmers remain.
        if len(farmers) < self.MIN_FARMERS:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Otherwise convert farmers into warriors while wheat allows.
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
        warriors_in_cave = [c for c in components if c.role == "Warrior"]

        # One-way switch: start the strike once a batch is gathered
        # or the time limit for the first attack is reached.
        if not self.strike and (len(warriors_in_cave) >= self.STRIKE_WARRIORS
                                or step >= self.STRIKE_STEP):
            self.strike = True

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack" if self.strike else "cave")
            else:
                # Farmers never fight; send them back to the Village.
                environment.assign_group(c, "village")