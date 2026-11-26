

Looking at the remaining failures, the key issues are:

1. **Warriors leaving cave too early**: Warriors sent to cave at `s_m >= 2` arrive with `s_m >= 3`, giving them < 2 attacks before needing to leave. Fix: only send warriors to cave when `s_m <= 1`, making them eat first when `s_m >= 2`.
2. **Not spawning when < 5 villagers**: Must spawn aggressively when population is low.
3. **Never spawning a farmer**: Must force at least one farmer spawn.
4. **Faster win**: Target more warriors (8), stagger eat cycles to maintain attack pressure.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_farmer = False

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        assigned = set()

        # Separate villagers
        warriors = []
        farmers = []
        eat_critical = []

        for c in components:
            if c.steps_since_meal >= 5:
                eat_critical.append(c)
            elif c.role == "Warrior":
                warriors.append(c)
            else:
                farmers.append(c)

        # Priority 1: Critical eat (will starve if not eating now)
        for c in eat_critical:
            environment.assign_group(c, "eat")
            assigned.add(id(c))

        total_warriors = len(environment.warriors)
        total_villagers = len(environment.warriors) + len(environment.farmers)
        wheat = environment.farm.wheat
        target_warriors = 8

        # Reserve wheat for meals (each villager needs ~1 per 5-6 steps)
        reserve = max(total_villagers + 3, 8)
        available_wheat = max(0, wheat - reserve)

        # --- Spawn logic ---
        spawn_warr_pairs = []  # pairs of farmers spawning a warrior
        spawn_farm_pairs = []  # pairs of farmers spawning a farmer

        # Must spawn warrior if 0 warriors exist
        if total_warriors == 0 and len(farmers) >= 2:
            if available_wheat >= 12:
                spawn_warr_pairs.append((farmers[0], farmers[1]))

        # Spawn warriors aggressively when under target
        if 0 < total_warriors < target_warriors:
            free_farmers = [f for f in farmers if f not in
                            (spawn_warr_pairs[0] if spawn_warr_pairs else [])]
            need = target_warriors - total_warriors
            max_pairs = min(len(free_farmers) // 2, available_wheat // 12, (need + 1) // 2)
            existing = set()
            for p in spawn_warr_pairs:
                existing.add(id(p[0]))
                existing.add(id(p[1]))
            unused = [f for f in free_farmers if id(f) not in existing]
            for i in range(max_pairs):
                if i * 2 + 1 < len(unused):
                    spawn_warr_pairs.append((unused[i * 2], unused[i * 2 + 1]))

        # Spawn if total villagers < 5 (optional constraint hint)
        if total_villagers < 5:
            existing_ids = set()
            for p in spawn_warr_pairs:
                existing_ids.add(id(p[0]))
                existing_ids.add(id(p[1]))
            for p in spawn_farm_pairs:
                existing_ids.add(id(p[0]))
                existing_ids.add(id(p[1]))
            free_f = [f for f in farmers if id(f) not in existing_ids]
            if len(free_f) >= 2 and available_wheat >= 10:
                # Spawn a warrior or farmer depending on what's lacking
                if total_warriors == 0:
                    spawn_warr_pairs.append((free_f[0], free_f[1]))
                else:
                    spawn_farm_pairs.append((free_f[0], free_f[1]))

        # Force spawn at least one farmer
        if not self._spawned_farmer and total_warriors >= 2:
            existing_ids = set()
            for p in spawn_warr_pairs:
                existing_ids.add(id(p[0]))
                existing_ids.add(id(p[1]))
            for p in spawn_farm_pairs:
                existing_ids.add(id(p[0]))
                existing_ids.add(id(p[1]))
            free_f = [f for f in farmers if id(f) not in existing_ids]
            if len(free_f) >= 2:
                used_cost = 12 * len(spawn_warr_pairs) + 10 * len(spawn_farm_pairs)
                if available_wheat - used_cost >= 10:
                    spawn_farm_pairs.append((free_f[0], free_f[1]))
                    self._spawned_farmer = True

        # Assign spawn warrior pairs
        for f1, f2 in spawn_warr_pairs:
            if id(f1) not in assigned:
                environment.assign_group(f1, "spawn warrior")
                assigned.add(id(f1))
            if id(f2) not in assigned:
                environment.assign_group(f2, "spawn warrior")
                assigned.add(id(f2))

        # Assign spawn farmer pairs
        for f1, f2 in spawn_farm_pairs:
            if id(f1) not in assigned:
                environment.assign_group(f1, "spawn farmer")
                assigned.add(id(f1))
            if id(f2) not in assigned:
                environment.assign_group(f2, "spawn farmer")
                assigned.add(id(f2))

        # --- Warrior movement ---
        # Only send warriors with s_m <= 1 to cave (ensures >= 2 attacks)
        # Warriors with s_m >= 2 should eat to reset
        spawn_used_ids = set()
        for p in spawn_warr_pairs:
            spawn_used_ids.add(id(p[0]))
            spawn_used_ids.add(id(p[1]))
        for p in spawn_farm_pairs:
            spawn_used_ids.add(id(p[0]))
            spawn_used_ids.add(id(p[1]))

        for w in warriors:
            if id(w) in assigned or id(w) in spawn_used_ids:
                continue
            if w.steps_since_meal <= 1:
                environment.assign_group(w, "cave")
                assigned.add(id(w))
            else:
                # Eat to reset hunger cycle for next cave trip
                environment.assign_group(w, "eat")
                assigned.add(id(w))

        # --- Remaining farmers farm ---
        for f in farmers:
            if id(f) not in assigned and id(f) not in spawn_used_ids:
                # Critical eat check (s_m >= 5 handled earlier, but just in case)
                if f.steps_since_meal >= 5:
                    environment.assign_group(f, "eat")
                else:
                    environment.assign_group(f, "farm")
                assigned.add(id(f))

        # Safety: assign anything still unassigned
        for c in components:
            if id(c) not in assigned:
                if c.role == "Warrior":
                    environment.assign_group(c, "eat")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            s_m = c.steps_since_meal

            # Must return to village at s_m >= 4
            # (arrive at village with s_m=5, eat that step before starving)
            if s_m >= 4:
                environment.assign_group(c, "village")
                continue

            # Critically low HP - retreat
            if c.hp <= 1:
                environment.assign_group(c, "village")
                continue

            # Otherwise attack the dragon
            environment.assign_group(c, "attack")
```