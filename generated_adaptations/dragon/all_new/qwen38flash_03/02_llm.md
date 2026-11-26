

Looking at this problem, I need to design a strategy that:
1. Gets warriors to the cave quickly to attack the dragon
2. Maintains food production (farmers) and warrior spawning
3. Manages hunger cycles (eat every 6 steps)
4. Balances attack pressure against dragon counter-attacks
5. Kills the dragon within 30 steps

**Strategy:**
- **Early game (steps 0-7):** Aggressively spawn warriors. Send warriors to cave immediately. Farmers farm for wheat.
- **Mid game (steps 7-20):** Warriors attack in cave, cycling back for food every ~5 steps. Farmers maintain wheat production. Stop spawning when we have ~7-8 warriors.
- **Late game (steps 20+):** All warriors attack to finish the dragon.
- **Food management:** Warriors sent back to village at `steps_since_meal >= 4` (arrive with 5, eat immediately). Critical eat at `>= 5`.
- **Cave strategy:** Attack unless about to starve or critically low HP.
- **Spawn logic:** Only spawn if we have < 8 warriors total and enough wheat surplus.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        if not components:
            return

        # Priority 1: Eat - critical hunger (steps_since_meal >= 5 means they'll starve next step)
        eat_list = [c for c in components if c.steps_since_meal >= 5]
        for c in eat_list:
            environment.assign_group(c, "eat")

        remaining = [c for c in components if c not in eat_list]
        if not remaining:
            return

        # Separate by role
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        wheat = environment.farm.wheat
        total_warriors_in_game = len(environment.warriors)

        # Priority 2: Spawn warriors in early-mid game if under target count
        spawn_w_list = []
        target_warriors = 8
        if step <= 10 and total_warriors_in_game < target_warriors:
            max_spawnable = (target_warriors - total_warriors_in_game)
            n_pairs = min(len(farmers) // 2, max_spawnable // 2)
            # Need 12 wheat per warrior spawned; keep reserve for meals
            # Estimate meals needed: all villagers in village might need eating soon
            reserve_wheat = max(3, len(components) // 2)
            affordable = max(0, (wheat - reserve_wheat)) // 12
            n_pairs = min(n_pairs, affordable)
            if n_pairs > 0:
                spawn_w_list = farmers[:n_pairs * 2]
                farmers = farmers[n_pairs * 2:]

        # Priority 3: Send warriors to cave (they will attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Priority 4: Assign farmers to spawn warrior group
        for f in spawn_w_list:
            environment.assign_group(f, "spawn warrior")

        # Priority 5: Remaining farmers farm for wheat
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if not components:
            return

        # Check if any villager in village is about to be hungry
        # and consider staggering: don't send ALL back at once
        # Strategy: send back those at steps_since_meal >= 4 (arrive at 5, eat safely)
        # Critical: steps_since_meal >= 5 must go NOW
        
        # Count how many are at critical hunger
        critical_hungry = [c for c in components if c.steps_since_meal >= 5]
        should_return = [c for c in components if c.steps_since_meal >= 4]
        low_hp = [c for c in components if c.hp <= 1]

        # Villagers that need to go back for food or are too weak
        must_return = list(set(id(c) for c in should_return + low_hp))
        
        for c in components:
            if id(c) in set(id(x) for x in should_return + low_hp):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```