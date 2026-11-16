## Adaptation strategy

The strategy keeps villagers alive, spawns the required units early, and keeps warriors cycling between the Cave and the Village so the Dragon is attacked often.

**Village phase**
1. **Feeding first:** Any villager with `steps_since_meal >= 3` goes to "eat". This leaves a margin below the 6-step starvation limit and also avoids sending a hungry warrior to the Cave.
2. **Wheat budget:** Available wheat is tracked after deducting one wheat per meal this step.
3. **Spawning:** Spawn groups are formed in pairs, since each spawn needs two villagers in the group.
   - Farmers are preferred as spawners so that warriors stay available for combat.
   - Warrior spawns (12 wheat each) are prioritised until two warriors have been spawned.
   - One farmer spawn (10 wheat) is then made.
   - Spawn counts are tracked internally, assuming each assigned spawn succeeds.
4. **Remaining villagers:** Farmers go to "farm". Healthy warriors that are not spawning go to "cave" while the Dragon is alive.

**Cave phase**
1. **Farmers** are never supposed to be in the Cave, so any that are sent to "village".
2. **Warriors with `steps_since_meal >= 4`** return to "village" to eat, so they do not starve.
3. **Other warriors** go to "attack". Their attacks keep the Dragon from regenerating, which the recommendation about attacking at least every 2 steps depends on.

The first-attack step is recorded so the "attack within the first 15 steps" recommendation can be checked. Cave-to-village trips take one step, so warriors rotate: one group attacks while another eats, which keeps the attack rate high.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers in the Village eat once they have gone this many steps without food.
    VILLAGE_EAT_THRESHOLD = 3
    # Villagers in the Cave return to the Village once they reach this many steps without food.
    CAVE_RETURN_THRESHOLD = 4
    WARRIOR_SPAWN_TARGET = 2
    FARMER_SPAWN_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.first_attack_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Feed hungry villagers first (eating consumes 1 wheat each).
        hungry = [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD]
        healthy = [c for c in components if c.steps_since_meal < self.VILLAGE_EAT_THRESHOLD]
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_left = wheat - len(hungry)

        # Spawners are chosen from the healthy villagers, preferring farmers
        # so that warriors stay available for combat.
        farmers = [c for c in healthy if c.role == "Farmer"]
        warriors = [c for c in healthy if c.role == "Warrior"]
        pool = farmers + warriors
        assigned = set()

        # 2) Spawn warriors (2 villagers + 12 wheat each) until the target is reached.
        while (self.warriors_spawned < self.WARRIOR_SPAWN_TARGET
               and wheat_left >= self.WARRIOR_COST
               and len([c for c in pool if id(c) not in assigned]) >= 2):
            pair = [c for c in pool if id(c) not in assigned][:2]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                assigned.add(id(c))
            self.warriors_spawned += 1
            wheat_left -= self.WARRIOR_COST

        # 3) Spawn farmers (2 villagers + 10 wheat each) until the target is reached.
        while (self.farmers_spawned < self.FARMER_SPAWN_TARGET
               and wheat_left >= self.FARMER_COST
               and len([c for c in pool if id(c) not in assigned]) >= 2):
            pair = [c for c in pool if id(c) not in assigned][:2]
            for c in pair:
                environment.assign_group(c, "spawn farmer")
                assigned.add(id(c))
            self.farmers_spawned += 1
            wheat_left -= self.FARMER_COST

        # 4) Everyone else: farmers farm, warriors go to the Cave to fight.
        dragon_alive = environment.dragon.hp > 0
        for c in healthy:
            if id(c) in assigned:
                continue
            if c.role == "Farmer":
                environment.assign_group(c, "farm")
            elif dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attacked_any = False
        for c in components:
            # Farmers must stay in the Village; starving or hungry villagers return to eat.
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                # Healthy, fed warriors attack every step to prevent regeneration.
                environment.assign_group(c, "attack")
                attacked_any = True

        if attacked_any and self.first_attack_step is None:
            self.first_attack_step = step
```