The earlier policies could reserve wheat so conservatively that they rarely spawned warriors, while also risking periods with too few attackers. This version prioritizes feeding villagers close to starvation, keeps only a minimal farming workforce when food is low, and uses available wheat and villagers to spawn warrior pairs without an arbitrary population cap. Cave villagers return at hunger 4, leaving time to travel back and eat before starving; everyone else attacks.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _hunger(villager):
        return int(getattr(villager, "steps_since_meal", 0))

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        population = len(environment.warriors) + len(environment.farmers)

        assigned = set()

        # Eat before assigning travel, work, or spawning. Account for meals
        # locally because the observable wheat value does not update on assign.
        hungry = sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        )
        for villager in hungry:
            if wheat < 1:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        available = [v for v in villagers if id(v) not in assigned]

        # Farm only when the stock is low, preferring farmers. One worker is
        # enough to begin replenishing food while the rest can fight or spawn.
        if dragon_hp > 0 and wheat < 12 and available:
            worker = next(
                (v for v in available if self._role(v) == "farmer"),
                available[0],
            )
            environment.assign_group(worker, "farm")
            assigned.add(id(worker))

        available = [v for v in villagers if id(v) not in assigned]

        # Pair villagers into warrior-spawn groups whenever the available
        # wheat can pay for them. Do not impose a low fixed population cap.
        spawn_pairs = min(len(available) // 2, wheat // 12)
        for villager in available[: 2 * spawn_pairs]:
            environment.assign_group(villager, "spawn warrior")
            assigned.add(id(villager))

        # Commit all remaining villagers to the assault (or keep farming after
        # the Dragon is dead, though normally the game ends immediately).
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            # Leave enough time for the one-step trip to the Village, then eat.
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```