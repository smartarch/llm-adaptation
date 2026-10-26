

## Analysis of Persistent Failure

The 0% win rate suggests multiple issues:
1. **Too few warriors attacking** means the Dragon's back-attacks (40% AoE damage + 20% eat) wipe out our attack force before dealing 50 damage.
2. **Spawning conditions too strict** — early game with few farmers, my spawn never triggered.
3. **Farmers never contributed to the attack** even when it was their best move (1 damage each still adds up; with 8 farmers that's 8 dmg/step).
4. **Late-game panic** was missing — when the timer runs low, everyone must swing at the Dragon.

## New Strategy

- **Phase 1 (steps 1–5, farm & send warriors):** All farmers farm. All warriors go to cave and attack. Spawn a warrior as soon as wheat ≥ 12 and we have ≥ 3 farmers (2 to spawn + 1 still farming). Spawn a farmer once we have wheat ≥ 10 and ≥ 4 farmers.
- **Phase 2 (mid-game):** Keep warriors in the cave attacking. Keep farmers farming/spawning. Send back any cave villager with HP ≤ 1 to preserve them.
- **Phase 3 (late-game, step ≥ 18 or dragon HP ≤ remaining attack budget):** Send ALL villagers to the cave and attack, no farming, no retreating. We must finish before step 30.
- **Dragon HP threshold check:** compute if we can kill in one big coordinated strike; if so, commit everyone.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.MAX_EXTRA_WARRIORS = 5
        self.MAX_EXTRA_FARMERS = 3

    def _assign_in_village_go_cave(self, env, c):
        env.assign_group(c, "cave")

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # --- Emergency: if dragon is nearly dead or we're late, send EVERYTHING to the cave ---
        late = step >= 18
        # estimate current max damage if all village villagers attacked now (1 per farmer, 3 per warrior)
        potential_dmg = sum(3 if c.role == "Warrior" else 1 for c in components)
        commit_all = late or dragon_hp <= potential_dmg

        if commit_all:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # --- Warriors always go to the cave to start attacking ASAP ---
        for w in warriors:
            self._assign_in_village_go_cave(environment, w)

        n_f = len(farmers)
        if n_f == 0:
            return

        # --- Spawning decisions for farmers ---
        # Need >=3 farmers to spawn (2 for the spawn group + at least 1 farming)
        can_spawn = n_f >= 3

        # Priority A: spawn warriors while we still want more offense
        if can_spawn and self.spawned_warriors < self.MAX_EXTRA_WARRIORS and wheat >= 12:
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            self.spawned_warriors += 1
            # the rest farm
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Priority B: spawn farmers to grow the economy
        if can_spawn and self.spawned_farmers < self.MAX_EXTRA_FARMERS and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            self.spawned_farmers += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Default: everyone farms
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        late = step >= 18

        # Estimate total damage if every villager in cave attacks this step
        total_dmg = sum(3 if c.role == "Warrior" else 1 for c in components)
        # If we can finish the dragon now, everyone swings
        finish_now = dragon_hp <= total_dmg

        for c in components:
            if finish_now or late:
                # All-out assault, do not send anyone back
                environment.assign_group(c, "attack")
            else:
                # Normal play: warriors attack, weak villagers retreat to preserve
                if c.hp <= 1:
                    environment.assign_group(c, "village")
                elif c.role == "Warrior":
                    environment.assign_group(c, "attack")
                else:
                    # Farmer in cave: usually send back to farm (1 dmg is low value)
                    environment.assign_group(c, "village")
```