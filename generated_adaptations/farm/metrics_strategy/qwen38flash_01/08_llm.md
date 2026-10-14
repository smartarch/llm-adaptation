

Looking at the score progression (166.3 → 172.0 → 241.7), my attempts to add complexity actually made things worse. The key insight I've been getting wrong: **partial protection IS effective, and transit time is extremely costly**. My code was releasing drones from fields prematurely and creating oscillation.

New strategy:
1. **Maximum stability**: Drones at an active field (threat > 0) NEVER get reassigned, even if the field is over-protected. They cost nothing to keep there.
2. **Release only truly dead fields**: Only pull drones from fields that have been threat=0 for 3+ consecutive steps.
3. **Greedy full protection**: Fill deficits from highest-threat field down using the pool of released + idle drones, sorted by distance.
4. **Never idle if there's a deficit**: Any drone not protecting an active field should go help the most threatened under-protected field.
5. **Respect drones in transit**: A drone with `state == "moving_to_field"` toward a valid target stays on that assignment regardless.

```py
import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    DEAD_FIELD_STEPS = 3  # keep drones on a field for this many steps after threat drops to 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._field_dead_steps = defaultdict(int)  # field_id -> consecutive steps at threat=0
        self._prev_assignments = {}  # drone_id -> field_id (or "idle")

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Update dead-field tracking ---
        for field in environment.fields:
            if field.threat_level <= 0:
                self._field_dead_steps[field.id] += 1
            else:
                self._field_dead_steps[field.id] = 0

        # --- Categorize drones ---
        # "locked" = drone is at a field with threat > 0, OR drone is in transit to such a field
        # "hold" = drone is at a field with threat == 0 but within grace period
        # "free" = drone is idle, or at a dead field past grace period
        locked_by_field = defaultdict(list)
        hold_drones = []   # (drone, field_id) - stay on dead field for now
        free_drones = []   # truly available for reassignment

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > 0:
                    # Active field - LOCK the drone here (never pull)
                    locked_by_field[tid].append(drone)
                else:
                    # Dead field - check grace period
                    if self._field_dead_steps[tid] < self.DEAD_FIELD_STEPS:
                        hold_drones.append((drone, tid))
                    else:
                        free_drones.append(drone)
            else:
                # No target or invalid target - drone is free
                free_drones.append(drone)

        # --- Sort active fields by threat level descending ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True
        )

        # --- Build assignment: locked drones keep their field ---
        drone_assignment = {}  # drone_id -> field_id or None

        for fid, drones in locked_by_field.items():
            for d in drones:
                drone_assignment[id(d)] = fid

        # Hold drones: keep them on their (dead) field for now
        for d, fid in hold_drones:
            drone_assignment[id(d)] = fid  # keep assignment even though field is dead

        # --- Pool of available drones for filling deficits ---
        pool = list(free_drones)

        # --- Greedy fill: go through active fields by priority ---
        for field in active_fields:
            fid = field.id
            have = len(locked_by_field.get(fid, []))
            need = field.drones_for_full_protection
            deficit = need - have

            if deficit <= 0:
                continue

            # Sort pool by distance to this field, pick closest ones
            pool.sort(key=lambda d: self._dist(d.location, field))
            take = pool[:deficit]
            pool = pool[deficit:]

            for d in take:
                drone_assignment[id(d)] = fid

        # --- If drones remain and fields are still under-protected, do partial ---
        if pool:
            # Recompute deficits
            for field in active_fields:
                fid = field.id
                have = len(locked_by_field.get(fid, []))
                # Also count newly assigned in this step
                newly_here = sum(1 for d in components if drone_assignment.get(id(d)) == fid and d not in locked_by_field.get(fid, []))
                have += newly_here
                need = field.drones_for_full_protection
                deficit = need - have
                if deficit <= 0:
                    continue
                pool.sort(key=lambda d: self._dist(d.location, field))
                take = pool[:deficit]
                pool = pool[deficit:]
                for d in take:
                    drone_assignment[id(d)] = fid

        # --- Remaining pool: assign to nearest threatened field with any deficit (partial) ---
        if pool and active_fields:
            for d in pool:
                # Find the field with highest threat that has fewest drones relative to need
                best_field = None
                best_score = float('inf')
                for field in active_fields:
                    fid = field.id
                    have = len(locked_by_field.get(fid, []))
                    newly_here = sum(1 for dd in components if drone_assignment.get(id(dd)) == fid and dd not in locked_by_field.get(fid, []))
                    have += newly_here
                    deficit = field.drones_for_full_protection - have
                    if deficit <= 0:
                        continue
                    # Score: distance normalized by deficit (prefer fields with bigger deficits)
                    dist = self._dist(d.location, field)
                    score = dist / (deficit + 1)
                    if score < best_score:
                        best_score = score
                        best_field = fid
                if best_field:
                    drone_assignment[id(d)] = best_field

        # --- Execute assignments ---
        for drone in components:
            did = id(drone)
            fid = drone_assignment.get(did)
            if fid is not None:
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(drone, group_name)
                else:
                    environment.assign_group(drone, "idle")
            else:
                environment.assign_group(drone, "idle")

        # --- Store for next step ---
        self._prev_assignments = {id(d): drone_assignment.get(id(d)) for d in components}
```