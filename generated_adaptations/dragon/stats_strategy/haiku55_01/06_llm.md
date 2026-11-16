## Revised strategy: tighter warrior cycle and multi-pair spawning

**What the last run showed:** The win rate rose to 33%, but only 1.4 villagers attacked per step on average. Warriors left the Cave at 4 steps without food and then spent several steps in the Village, so many Cave steps had no attackers. Spawning also stopped after the first few steps, and the Dragon was still at 8 HP on average in the losses.

**Changes:**

1. **Shorter, fixed warrior cycle.** Warriors leave the Cave once `steps_since_meal` reaches 3. The next step they are in the Village at count 4, eat, and return to the Cave in the following step. Each cycle is about 4 steps: 3 attack steps and 1 meal step. That keeps a warrior attacking about 75% of the time, well below the 6-step starvation limit, with a margin of 2 steps.
2. **Warriors eat as soon as they are back.** In the Village, a warrior that is not fresh (`steps_since_meal >= 1`) eats immediately. A warrior that has just eaten (count 0) goes straight back to the Cave, so the cave population stays high and the Village only holds warriors for one step.
3. **Farmers keep the economy running.** Farmers eat only when `steps_since_meal >= 3`. Otherwise they farm, which keeps wheat income high enough for repeated spawns.
4. **Aggressive multi-pair spawning.** Each step, as many "spawn warrior" pairs of farmers as the wheat budget allows are formed after meals are reserved. Early warriors compound damage, since the Dragon must be killed within 30 steps. Spawning never uses wheat needed for meals.
5. **Farmers never enter the Cave.** They have 4 HP and only 1 damage, so they add little in combat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors run a short cycle: ~3 attack steps in the Cave, then return to the Village
      to eat immediately and go straight back. This keeps most warriors attacking each step.
    - Farmers eat only when needed (threshold 3) and otherwise farm wheat.
    - Meals are reserved first; the rest of the wheat is used for as many
      "spawn warrior" pairs (2 farmers per 12 wheat) as possible each step.
    - Farmers never enter the Cave.
    """

    WARRIOR_LEAVE_CAVE_AT = 3   # warriors in the Cave return once this many steps have passed
    FARMER_EAT_AT = 3           # farmers eat at this threshold
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals first.
        eaters = []
        for c in warriors:
            # Warriors that are not freshly fed eat right away; fresh ones (0 steps) go back to the Cave.
            if c.steps_since_meal >= 1:
                eaters.append(c)
        for c in farmers:
            if c.steps_since_meal >= self.FARMER_EAT_AT:
                eaters.append(c)

        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        eater_ids = {id(c) for c in eaters}
        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Spawn warriors with as many farmer pairs as the wheat budget allows.
        spawn_ids = set()
        while wheat >= self.WARRIOR_COST and len(idle_farmers) >= 2:
            pair = idle_farmers[:2]
            idle_farmers = idle_farmers[2:]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 3) Fresh warriors head to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 4) Remaining farmers farm wheat.
        for c in idle_farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```