import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, loc, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        field_by_id = {f.id: f for f in environment.fields}

        # --- Categorize drones based on their current target ---
        # locked: at a field with threat > 0 (should stay)
        # semi_free: at a field with threat == 0 (can be pulled if needed)
        # free: no target at all
        locked_by_field = defaultdict(list)
        semi_free = []  # (drone, field_id)
        free = []

        for drone in components:
            tid = drone.target_id
            if tid is not None and tid in field_by_id:
                fld = field_by_id[tid]
                if fld.threat_level > 0:
                    locked_by_field[tid].append(drone)
                else:
                    semi_free.append(drone)
            else:
                free.append(drone)

        # --- Release over-protected drones from active fields ---
        for fid in list(locked_by_field.keys()):
            fld = field_by_id[fid]
            max_allowed = fld.drones_for_full_protection
            if len(locked_by_field[fid]) > max_allowed:
                # Keep the ones that are "protecting" (already there), release moving ones
                drones_here = locked_by_field[fid]
                # Sort: protecting drones first, then moving ones
                drones_here.sort(key=lambda d: 0 if d.state == "protecting" else 1)
                keep = drones_here[:max_allowed]
                release = drones_here[max_allowed:]
                locked_by_field[fid] = keep
                for d in release:
                    free.append(d)

        # --- Sort active fields by threat descending ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True
        )

        # --- Pool of available drones to assign (free first, then semi_free) ---
        # We'll try free drones before semi_free to minimize movement
        pool_free = list(free)
        pool_semi = list(semi_free)

        assignments = {}  # drone_id -> group_name or None

        # --- Locked drones keep their assignment ---
        for fid, drones in locked_by_field.items():
            for d in drones:
                assignments[id(d)] = f"protecting {fid}"

        # --- Phase 1: Full protection of active fields, highest threat first ---
        for field in active_fields:
            fid = field.id
            have = len(locked_by_field.get(fid, []))
            need = field.drones_for_full_protection
            deficit = need - have
            if deficit <= 0:
                continue

            # Use free drones first (closest to this field)
            if pool_free and deficit > 0:
                pool_free.sort(key=lambda d: self._dist(d.location, field))
                take = pool_free[:deficit]
                pool_free = pool_free[deficit:]
                deficit -= len(take)
                for d in take:
                    assignments[id(d)] = f"protecting {fid}"

            # Then use semi_free drones if still needed
            if pool_semi and deficit > 0:
                pool_semi.sort(key=lambda d: self._dist(d.location, field))
                take = pool_semi[:deficit]
                pool_semi = pool_semi[deficit:]
                deficit -= len(take)
                for d in take:
                    assignments[id(d)] = f"protecting {fid}"

        # --- Phase 2: Partial protection of under-protected fields ---
        # Fields that are still under-protected after phase 1
        if pool_free or pool_semi:
            remaining_pool = pool_free + pool_semi
            # Count current drones per field (including just-assigned)
            current_per_field = defaultdict(int)
            for fid, drones in locked_by_field.items():
                current_per_field[fid] = len(drones)
            # Add newly assigned
            for did, gn in assignments.items():
                if gn.startswith("protecting "):
                    fid = gn[len("protecting "):]
                    current_per_field[fid] += 1

            for field in active_fields:
                fid = field.id
                have = current_per_field.get(fid, 0)
                need = field.drones_for_full_protection
                deficit = need - have
                if deficit <= 0:
                    continue
                if not remaining_pool:
                    break
                remaining_pool.sort(key=lambda d: self._dist(d.location, field))
                # Give partial protection: up to deficit drones, but at least 1 if available
                take = remaining_pool[:deficit]
                remaining_pool = remaining_pool[deficit:]
                for d in take:
                    assignments[id(d)] = f"protecting {fid}"
                    current_per_field[fid] += 1

        # --- Phase 3: Semi_free drones that weren't reassigned stay at their old field ---
        # (they're a nearby reserve; if all fields are covered, this is fine)
        if pool_semi:
            for d in pool_semi:
                if id(d) not in assignments:
                    old_fid = d.target_id
                    if old_fid and old_fid in field_by_id:
                        # Keep them at the dead field as a reserve
                        assignments[id(d)] = None  # idle for now
                    else:
                        assignments[id(d)] = None

        # Phase 3b: Remaining free drones with no assignment
        for d in remaining_pool:
            if id(d) not in assignments:
                assignments[id(d)] = None

        # --- Final: assign all drones to groups ---
        for drone in components:
            did = id(drone)
            gn = assignments.get(did)
            if gn is not None and gn in group_ids:
                environment.assign_group(drone, gn)
            else:
                environment.assign_group(drone, "idle")