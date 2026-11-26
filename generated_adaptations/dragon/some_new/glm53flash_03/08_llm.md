## Analysis

Two problems: (1) a bookkeeping bug caused a component to be assigned twice in some cases — I'll add a strict deduplication guard so every component is assigned exactly once; (2) the win rate collapsed to 0% because the strategy became too timid — feeding at `>=3` and retreating at `hp<=2` made villagers ping-pong between the Village and the Cave instead of attacking. I'll revert to the aggressive timing (eat/retreat at `>=4`), keep 1–2 farmers farming, and add an all-in push when the Dragon is nearly dead.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        assigned = set()

        def put(c, group):
            if id(c) not in assigned:
                groups[group].append(c)
                assigned.add(id(c))

        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)
        total = n_farmers + n_warriors
        reserve = total  # keep one meal per villager as reserve

        # 1) Feeding first: anyone at risk of starving eats now.
        for c in components:
            if c.steps_since_meal >= 4:
                if wheat >= 1:
                    put(c, "eat")
                    wheat -= 1
                else:
                    put(c, "farm")

        rest = [c for c in components if id(c) not in assigned]

        # 2) Aggressive spawning: warriors are the key to a fast kill.
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        if wheat >= 12 + reserve and len(rest) >= 2 and n_warriors < 10:
            pair = (warriors_here + farmers_here + rest)[:2]
            for c in pair:
                put(c, "spawn warrior")
            wheat -= 12
        elif total < 5 and wheat >= 10 + reserve and len(rest) >= 2:
            pair = (farmers_here + rest)[:2]
            for c in pair:
                put(c, "spawn farmer")
            wheat -= 10

        rest = [c for c in components if id(c) not in assigned]
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # 3) Warriors march to the Cave; farmers farm or reinforce the Cave.
        for c in warriors_here:
            put(c, "cave")
        farmers_here.sort(key=lambda c: -c.hp)
        n_farm_to_farm = 2 if total <= 5 else 1
        for i, c in enumerate(farmers_here):
            put(c, "farm" if i < n_farm_to_farm else "cave")

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        dragon_hp = environment.dragon.hp

        for c in components:
            # Starving villagers are too weak to damage the Dragon;
            # send them (and the badly hurt) home to eat and recover.
            # All-in push when the Dragon is nearly dead.
            if dragon_hp > 15 and (c.steps_since_meal >= 4 or c.hp <= 2):
                groups["village"].append(c)
            else:
                groups["attack"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)
```