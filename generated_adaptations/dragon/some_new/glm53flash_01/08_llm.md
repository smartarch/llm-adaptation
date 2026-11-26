The regression came from the final push at HP ≤ 40: it emptied the Village of farmers, wheat and food production collapsed, villagers starved and the Dragon slaughtered a starving army — win rate dropped to 33%. Fix: the final push is restricted to warriors only (farmers keep farming) and triggers at HP ≤ 30. The remaining wheat-shortage failure is fixed by a larger safety margin (reserve covers everyone with `steps_since_meal >= 2`, plus a +2 buffer before any spawning).

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon

        # Meals due in the near future across ALL villagers (Village + Cave).
        # Generous margin: everyone with steps_since_meal >= 2 must be able
        # to eat within the next couple of steps (including travel home).
        everyone = list(environment.farmers) + list(environment.warriors)
        reserve = sum(1 for c in everyone if c.steps_since_meal >= 2)

        # 1) Eat first: everyone in the Village who must eat now.
        hungry = sorted(
            (c for c in components if c.steps_since_meal >= 4),
            key=lambda c: -c.steps_since_meal,
        )
        fed = []
        for c in hungry:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                fed.append(c)
            else:
                break  # no wheat left; they must farm this step

        remaining = [c for c in components if c not in fed]

        # 2) Final push: when the Dragon is nearly dead, send the warriors
        #    (farmers stay and keep the economy/food running).
        if dragon.hp <= 30:
            for c in list(remaining):
                if c.role == "Warrior":
                    environment.assign_group(c, "cave")
                    remaining.remove(c)
            for c in remaining:
                environment.assign_group(c, "farm")
            return

        # 3) Warriors travel to the Cave (they are useless on the farm).
        for c in list(remaining):
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                remaining.remove(c)

        # 4) Spawn warriors when affordable while keeping the meal reserve
        #    plus a small safety buffer.
        i = 0
        while i + 1 < len(remaining) and wheat - 12 >= reserve + 2:
            environment.assign_group(remaining[i], "spawn warrior")
            environment.assign_group(remaining[i + 1], "spawn warrior")
            wheat -= 12
            i += 2
        remaining = remaining[i:]

        # 5) Spawn farmers only with a large surplus (economy growth).
        while (
            len(remaining) >= 2
            and wheat - 10 >= reserve + 7
            and len(environment.farmers) < 8
        ):
            environment.assign_group(remaining[0], "spawn farmer")
            environment.assign_group(remaining[1], "spawn farmer")
            wheat -= 10
            remaining = remaining[2:]

        # 6) Everyone else farms.
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 3:
                # Head home now: arrives in the Village next step (ssm 4-5)
                # and can still eat before starving (ssm 6).
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```

Key changes:

- **Final push toned down**: threshold back to HP ≤ 30 and only warriors are sent; farmers keep farming so wheat keeps flowing and nobody starves during the end-game. This should restore the 67% win rate while still finishing the Dragon quickly.
- **Reserve widened to `steps_since_meal >= 2`** plus a **+2 buffer** before spawning warriors and **+7** before spawning farmers — this fixes the "0 wheat left, Jeff must eat next step" violation (the buffer also covers newly spawned cave returners and rounding in wheat production).
- Farmer spawning is capped at 8 farmers to avoid over-investing in the economy when the Dragon could die soon.