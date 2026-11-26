

Looking at this problem, I need to design a strategy that:
1. Builds up warriors quickly (3 damage each vs dragon's 100 HP)
2. Manages hunger (eat every ~6 steps, with travel time to/from cave)
3. Maintains wheat production for feeding and spawning
4. Rotates villagers through the cave for sustained damage output

**Strategy overview:**
- **Village priority**: Eat (if hungry) → Spawn warriors (aggressively in early game) → Warriors to cave (if well-fed and healthy) → Farm
- **Cave priority**: Return to village (if sme ≥ 3 or low HP) → Attack everyone else
- **Late game all-in** (step ≥ 22): Send everyone to cave for final push
- **Wheat management**: Don't send to cave if wheat critically low; prioritize farming

Key timing: A warrior with sme=0 goes to cave, can attack for 3 steps, then returns (sme=4 in village, eats). This creates a rotation cycle.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Categorize villagers by hunger and role
        hungry = []
        warriors_ok = []
        farmers_ok = []

        for c in components:
            if c.steps_since_meal >= 4:
                hungry.append(c)
            elif c.role == "Warrior":
                warriors_ok.append(c)
            else:
                farmers_ok.append(c)

        # --- Spawning logic ---
        spawn_warrior_pool = []
        spawn_farmer_pool = []

        # Aggressively spawn warriors early to build damage output
        # Use farmers as spawn partners (they lose 5 wheat for a step but we gain a warrior)
        if step < 12:
            # Early game: very aggressive spawning
            while (wheat > 30 + len(hungry) + 5 and
                   len(farmers_ok) >= 2 and
                   len(spawn_warrior_pool) < 4):
                spawn_warrior_pool.append(farmers_ok.pop(0))
                spawn_warrior_pool.append(farmers_ok.pop(0))

            # If we have very few warriors, try harder
            total_warriors = len(environment.warriors)
            if total_warriors < 3 and wheat > 25 and len(farmers_ok) >= 2:
                spawn_warrior_pool.append(farmers_ok.pop(0))
                spawn_warrior_pool.append(farmers_ok.pop(0))
        else:
            # Mid/late game: spawn if well-resourced
            if wheat > 50 and len(farmers_ok) >= 4:
                spawn_warrior_pool.append(farmers_ok.pop(0))
                spawn_warrior_pool.append(farmers_ok.pop(0))

            # Spawn farmers if critically short on food producers
            total_farmers = len(environment.farmers)
            if total_farmers < 2 and wheat >= 20 and len(farmers_ok) >= 2:
                spawn_farmer_pool.append(farmers_ok.pop(0))
                spawn_farmer_pool.append(farmers_ok.pop(0))

        # --- Cave assignment ---
        cave_pool = []
        total_villagers = len(environment.warriors) + len(environment.farmers)

        # Late game all-in: step >= 22, push everyone
        if step >= 22 and dragon_hp > 0:
            for w in warriors_ok:
                if w.steps_since_meal < 4:
                    cave_pool.append(w)
            for f in farmers_ok:
                if f.steps_since_meal < 4:
                    cave_pool.append(f)
            warriors_ok = [w for w in warriors_ok if w not in cave_pool]
            farmers_ok = [f for f in farmers_ok if f not in cave_pool]
        else:
            # Normal: send warriors to cave if they can sustain the rotation
            # sme=0: travel(1) + 3 attack + travel back(1) = arrive eat at sme=5, OK
            # sme=1: travel(1) + 2 attack + travel back(1) = arrive eat at sme=5, OK
            # sme=2: travel(1) + 1 attack + travel back(1) = arrive eat at sme=5, tight
            # Only send if wheat is sufficient for feeding
            if wheat >= 5:
                for w in warriors_ok:
                    if w.steps_since_meal <= 1 and w.hp >= 3:
                        cave_pool.append(w)
                    elif w.steps_since_meal == 2 and w.hp >= 5:
                        # Tight timing, allow if healthy
                        cave_pool.append(w)
                # In mid-game if we have surplus farmers, send a couple to help
                if len(warriors_ok) < 4 and len(farmers_ok) > 5 and wheat > 40:
                    for f in farmers_ok[:2]:
                        if f.steps_since_meal == 0:
                            cave_pool.append(f)
                            farmers_ok.remove(f)

        # --- Everyone else farms ---
        farm_pool = farmers_ok + [w for w in warriors_ok if w not in cave_pool]

        # --- Execute assignments ---
        for c in hungry:
            environment.assign_group(c, "eat")
        for c in spawn_warrior_pool:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer_pool:
            environment.assign_group(c, "spawn farmer")
        for c in cave_pool:
            environment.assign_group(c, "cave")
        for c in farm_pool:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Must return to village to eat: sme>=3 means arrive village at sme=4, eat at sme=4 (safe)
            # If sme=4, arrive village at sme=5, must eat next step (last moment)
            if c.steps_since_meal >= 4:
                # Critical: must leave NOW, arrive at sme=5, eat that step
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= 3:
                # Safe return
                environment.assign_group(c, "village")
            elif c.hp <= 2:
                # Too damaged, retreat to avoid death
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")
```