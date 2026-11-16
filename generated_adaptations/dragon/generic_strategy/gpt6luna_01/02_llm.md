The strategy keeps farmers in the Village to maintain food production, while using surplus wheat to spawn villagers—first a Farmer when the local farming workforce is small, then Warriors when there are enough Farmers to keep the farm staffed. Village villagers eat before they become urgently hungry. Cave Warriors attack while healthy and fed, with staggered returns for meals; dangerously injured or hungry villagers return to the Village. Farmers caught in the Cave return unless a Farmer is needed to keep the Dragon under attack.

Every component is explicitly assigned on every call. The code uses the group names directly as the `group_id` values.```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = environment.farm.wheat

        # Eat before hunger becomes dangerous. Villagers assigned to eat
        # remain in the Village for this step.
        assignments = {}
        for villager in villagers:
            if villager.steps_since_meal >= 4:
                assignments[villager] = "eat"

        # Use eligible Farmers for spawning, while keeping at least one
        # Farmer on the farm whenever the local workforce is large enough.
        eligible_farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]
        farmer_count = sum(v.role == "Farmer" for v in villagers)

        spawn_group = None
        if farmer_count <= 2 and len(eligible_farmers) >= 2:
            # Build up the food-producing workforce when it is small.
            spawn_group = "spawn farmer"
            max_pairs = 1
        elif farmer_count >= 3 and len(eligible_farmers) >= 3:
            # Keep at least one eligible Farmer farming.
            spawn_group = "spawn warrior"
            max_pairs = (len(eligible_farmers) - 1) // 2
        else:
            max_pairs = 0

        if spawn_group is not None:
            cost = 10 if spawn_group == "spawn farmer" else 12
            # Hold wheat back for meals and unexpected returns from the Cave.
            reserve = max(10, 2 * len(villagers) + 6)
            affordable_pairs = max(0, (wheat - reserve) // cost)
            pairs_to_spawn = min(max_pairs, affordable_pairs)

            for villager in eligible_farmers[: 2 * pairs_to_spawn]:
                assignments[villager] = spawn_group

        for villager in villagers:
            if villager not in assignments:
                if villager.role == "Warrior":
                    assignments[villager] = "cave"
                else:
                    assignments[villager] = "farm"

        for villager in villagers:
            self._assign(environment, villager, assignments[villager])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp

        # Work out which Warriors can keep attacking. Returning at hunger
        # level 3 is staggered; by level 4, everyone returns to eat.
        warrior_attacks = {}
        for i, villager in enumerate(villagers):
            if villager.role != "Warrior":
                continue

            can_finish_now = dragon_hp <= 3 and villager.hp > 1
            if villager.hp <= 1 and not can_finish_now:
                warrior_attacks[villager] = False
            elif villager.steps_since_meal >= 4 and not can_finish_now:
                warrior_attacks[villager] = False
            elif villager.steps_since_meal == 3 and not can_finish_now:
                warrior_attacks[villager] = ((step + i) % 3 != 0)
            else:
                warrior_attacks[villager] = True

        active_warrior = any(warrior_attacks.values())
        assignments = {}

        for i, villager in enumerate(villagers):
            if villager.role == "Warrior":
                assignments[villager] = (
                    "attack" if warrior_attacks[villager] else "village"
                )
                continue

            # Farmers are generally more useful producing food in the
            # Village. If no Warrior can attack, keep one healthy, fed
            # Farmer attacking to avoid leaving the Dragon unpressured.
            if dragon_hp <= 1 and villager.hp > 1:
                assignments[villager] = "attack"
            elif (
                not active_warrior
                and villager.hp > 1
                and villager.steps_since_meal < 3
                and not any(
                    v.role == "Farmer" and assignments.get(v) == "attack"
                    for v in villagers
                )
            ):
                assignments[villager] = "attack"
            else:
                assignments[villager] = "village"

        for villager in villagers:
            self._assign(environment, villager, assignments[villager])
```