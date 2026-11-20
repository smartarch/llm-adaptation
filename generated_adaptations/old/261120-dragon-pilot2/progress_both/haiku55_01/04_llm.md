## Analysis of the previous run

The logs point to four problems:

1. **Too few attacks.** Warriors were sent to the Cave only when they had just eaten, and they returned after a single attack. The Dragon was attacked on only about half the steps, so it regenerated 5 HP on the other steps and healed back to 80–100 HP.
2. **Spawning stopped too early.** The spawn window closed at step 20, but in Game 3 wheat piled up to 188 unused, while the army stayed at 2 warriors.
3. **Farmers were not used for the economy.** Farmers produce 5 wheat per step, which is more than twice a warrior's output. Early farmer spawns would have paid back quickly.
4. **Reserve logic was too conservative.** It blocked spawns even when wheat was plentiful later on.

## New approach

**Goal:** build a warrior force quickly, then keep at least one or two warriors attacking every step so the Dragon never gets a free regeneration turn.

**Village rules (`assign_in_village`):**
- **Eat first.** Farmers eat at `steps_since_meal >= 3`, and warriors eat at `>= 2`. Warriors are checked first, since they cannot reach the Cave in time otherwise. Meals are funded from wheat in priority order (longest unfed first).
- **Economy spawns (steps 1–8).** Until there are 4 farmers, free farmers form pairs and spawn a Farmer (10 wheat) whenever wheat exceeds a small reserve. Farmers pay back their cost in about two steps.
- **Army spawns (up to step 24).** After that, free farmer pairs spawn Warriors (12 wheat) whenever wheat covers the reserve.
- **Attack dispatch.** Warriors that are not eating go to the Cave. Warriors that just ate are sent out, and they have 3 steps of attacks before they return.
- **Default.** All remaining farmers farm.

**Cave rules (`assign_in_cave`):**
- Warriors attack unless `steps_since_meal >= 3` or HP is critically low (≤ 1), in which case they return to the Village to eat.
- Farmers that end up in the Cave go back to the Village.

With several warriors cycling through the Cave, one or more attack every step. The Dragon takes 3 damage per warrior-attack and regenerates only on steps with no attacks.

## Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy first (farmers spawn farmers early), then a growing warrior army
    that rotates between the Cave (attacking) and the Village (eating), so the
    Dragon is attacked almost every step and never gets free regeneration.
    """

    FARMER_EAT_AT = 3       # farmers eat when they have gone this many steps unfed
    WARRIOR_EAT_AT = 2      # warriors eat early so they can afford a Cave trip
    CAVE_RETURN_AT = 3      # warriors in the Cave go home at this hunger level
    CAVE_RETURN_HP = 1      # ... or when nearly dead
    FARMER_TARGET = 4       # build up to this many farmers early
    FARMER_SPAWN_UNTIL = 8  # economy spawns only until this step
    WARRIOR_SPAWN_UNTIL = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Decide who eats: warriors first, then the most hungry villagers.
        def eat_threshold(c):
            return self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT

        hungry = [c for c in components if c.steps_since_meal >= eat_threshold(c)]
        hungry.sort(key=lambda c: (c.role != "Warrior", -c.steps_since_meal))

        eating = []
        for c in hungry:
            if wheat >= 1:
                eating.append(c)
                wheat -= 1
        eating_ids = {id(c) for c in eating}

        for c in eating:
            environment.assign_group(c, "eat")

        # 2) Everyone else who is not eating.
        rest = [c for c in components if id(c) not in eating_ids]
        farmers_free = [c for c in rest if c.role == "Farmer"]
        warriors_free = [c for c in rest if c.role == "Warrior"]

        # Keep a small wheat reserve for the next round of meals.
        reserve = max(2, len(components) // 2)
        total_farmers = sum(1 for c in components if c.role == "Farmer")

        spawned_ids = set()

        # 3) Spawn using pairs of free farmers.
        while len(farmers_free) - len(spawned_ids) >= 2:
            pair = [f for f in farmers_free if id(f) not in spawned_ids][:2]

            if step <= self.FARMER_SPAWN_UNTIL and total_farmers < self.FARMER_TARGET \
                    and wheat - reserve >= 10:
                group = "spawn farmer"
                wheat -= 10
                total_farmers += 1
            elif step <= self.WARRIOR_SPAWN_UNTIL and wheat - reserve >= 12:
                group = "spawn warrior"
                wheat -= 12
            else:
                break

            for f in pair:
                environment.assign_group(f, group)
                spawned_ids.add(id(f))

        # 4) Remaining farmers farm.
        for f in farmers_free:
            if id(f) not in spawned_ids:
                environment.assign_group(f, "farm")

        # 5) Warriors that are not eating go to the Cave to attack.
        for w in warriors_free:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers do not belong in the Cave.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_AT or c.hp <= self.CAVE_RETURN_HP:
                # Hungry or nearly dead warriors go home to eat / recover.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```