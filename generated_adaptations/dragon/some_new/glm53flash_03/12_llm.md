## Analysis

Best result so far was the version that fed at `>=3` and retreated at `>=3`/`hp<=2` (67% win rate). I'll restore that configuration, keep the deduplication guard, and add a final all-in push that only bypasses the *low-HP* retreat (never the eating rule, which must always hold).

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
            if c.steps_since_meal >= 3:
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
            # Eating rule is absolute: hungry villagers go home now.
            if c.steps_since_meal >= 3:
                groups["village"].append(c)
            # Badly hurt villagers retreat to recover, unless we are
            # making the final all-in push on a nearly dead Dragon.
            elif c.hp <= 2 and dragon_hp > 15:
                groups["village"].append(c)
            else:
                groups["attack"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)
```