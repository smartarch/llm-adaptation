## Revised strategy: budgeted meals, early farmer growth, then a warrior strike force

**What failed:** The test reports show two problems. First, the village logic spent wheat on spawning without reserving enough for the meals that were already due, so a hungry warrior (Robert) could not be assigned to "eat" and was left unassigned. Second, the spawning was too slow to reach the Dragon's 100 HP in 30 steps.

**Changes:**

1. **Meals are funded first.** Hungry villagers (`steps_since_meal >= 3`) are sorted by hunger, and each one gets "eat" only while wheat remains. Any hungry villager that cannot be fed is still assigned to a group (farm), so every component is covered. Meals are never assigned without wheat.
2. **Spawning uses only the leftover wheat.** Spawns are allowed only when `wheat - meals - reserve` covers the cost. The reserve keeps wheat for the next step's meals.
3. **Early farmers as an economy.** A farmer costs 10 wheat and produces 5 per step, so it pays for itself in about two steps. Early in the game the strategy spawns farmers to build wheat income. Later it switches to warriors for damage.
4. **Warriors attack in rotation.** Fed warriors in the Village go to the Cave. Warriors in the Cave attack while `steps_since_meal < 3`, then return to eat. This keeps the damage going while every warrior eats well before the 6-step limit.
5. **Every component is assigned exactly once.** Each villager is placed by index into one group, which avoids double or missing assignments.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Hungry villagers (steps_since_meal >= HUNGER_LIMIT) eat first, but only
      as many as the wheat stock allows. Meals are never assigned without wheat.
    - Spawning uses only the wheat left after meals, minus a small reserve.
    - Early game: spawn farmers (cheap, produce 5 wheat/step) to build income.
      Later: spawn warriors for damage.
    - Fed warriors attack the Dragon from the Cave and return to the Village
      before they starve. Farmers stay on the farm.
    - Every component is assigned exactly once per call.
    """

    HUNGER_LIMIT = 3       # eat when steps_since_meal reaches this value
    MAX_WARRIORS = 8       # stop spawning warriors beyond this count
    MAX_FARMERS = 6        # stop spawning farmers beyond this count
    FARMER_COST = 10
    WARRIOR_COST = 12
    RESERVE = 2            # wheat kept aside for the next step's meals
    FARMER_PHASE_STEPS = 10  # spawn farmers for economy only in early steps

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        assigned = set()

        # 1. Meals: feed the hungriest villagers first, as far as wheat allows.
        hungry = [i for i, c in enumerate(comps) if c.steps_since_meal >= self.HUNGER_LIMIT]
        hungry.sort(key=lambda i: comps[i].steps_since_meal, reverse=True)
        for i in hungry:
            if wheat >= 1:
                environment.assign_group(comps[i], "eat")
                assigned.add(i)
                wheat -= 1
        # Hungry villagers that could not be fed still need a group.
        for i in hungry:
            if i not in assigned:
                environment.assign_group(comps[i], "farm")
                assigned.add(i)

        # 2. Spawning from fed villagers, using only the leftover wheat.
        fed_farmers = [i for i, c in enumerate(comps)
                       if i not in assigned and c.role == "Farmer"]
        n_warriors = len(environment.warriors)
        n_farmers = len(environment.farmers)
        spare = wheat - self.RESERVE

        spawn_pair = None
        if dragon_alive and len(fed_farmers) >= 2:
            if (step < self.FARMER_PHASE_STEPS
                    and n_farmers < self.MAX_FARMERS
                    and spare >= self.FARMER_COST):
                spawn_pair = ("spawn farmer", fed_farmers[:2])
            elif (n_warriors < self.MAX_WARRIORS
                    and spare >= self.WARRIOR_COST):
                spawn_pair = ("spawn warrior", fed_farmers[:2])

        if spawn_pair is not None:
            group, idxs = spawn_pair
            for i in idxs:
                environment.assign_group(comps[i], group)
                assigned.add(i)

        # 3. Everyone else who is fed.
        for i, c in enumerate(comps):
            if i in assigned:
                continue
            if c.role == "Warrior" and dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.HUNGER_LIMIT:
                # Healthy warriors keep hitting the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and farmers return to the Village.
                environment.assign_group(c, "village")
```