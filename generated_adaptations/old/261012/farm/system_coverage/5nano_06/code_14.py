from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center(self, f):
        return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

    def _dist_to_field(self, d, f):
        loc = getattr(d, "location", None)
        if loc is None:
            return float("inf")
        cx, cy = self._center(f)
        x = getattr(loc, "x", 0.0)
        y = getattr(loc, "y", 0.0)
        return math.hypot(x - cx, y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat
        fields = [fld for fld in environment.fields if getattr(fld, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat level (highest first)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        field_ids = {f.id for f in fields_sorted}

        # 3) Build initial allocations: drones currently protecting or moving toward a field
        final_alloc = {f.id: set() for f in fields_sorted}
        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if tid in field_ids and st in ("protecting", "moving_to_field"):
                final_alloc[tid].add(d)

        # 4) Build surplus from fields that have more protectors than their own need
        surplus = []  # list of (drone, src_field_id)
        for f in fields_sorted:
            current = list(final_alloc[f.id])
            need = max(int(getattr(f, "drones_for_full_protection", 0)), 0)
            if len(current) > need:
                current.sort(key=lambda d: self._dist_to_field(d, f))
                keep = current[:need]
                extra = current[need:]
                final_alloc[f.id] = set(keep)
                for d in extra:
                    surplus.append((d, f.id))

        # Helper to allocate from surplus to a target field
        def allocate_from_surplus(target_field, final_alloc, surplus_pool):
            need = max(int(getattr(target_field, "drones_for_full_protection", 0)), 0) - len(final_alloc[target_field.id])
            while need > 0 and surplus_pool:
                # choose the surplus drone closest to the target field
                best_idx = min(range(len(surplus_pool)), key=lambda i: self._dist_to_field(surplus_pool[i][0], target_field))
                drone, src = surplus_pool.pop(best_idx)
                final_alloc[target_field.id].add(drone)
                need -= 1
            return need

        # 5) Use surplus to fill top field first, then others in threat order
        # Fill top field from surplus
        top_field = fields_sorted[0]
        if len(final_alloc[top_field.id]) < max(int(getattr(top_field, "drones_for_full_protection", 0)), 0) and surplus:
            allocate_from_surplus(top_field, final_alloc, surplus)

        # If still not full, use idle drones (closest first)
        if len(final_alloc[top_field.id]) < max(int(getattr(top_field, "drones_for_full_protection", 0)), 0) and surplus:
            # Re-run surplus in case we added new ones; but if surplus is empty, use idle
            pass

        # Gather idle drones (truly idle: state == "idle" and no target)
        # We'll allocate to fill remaining needs for further fields
        idle_drones = [d for d in components if getattr(d, "state", "") == "idle" and getattr(d, "target_id", None) is None]
        # Allocate remaining needs for all fields in threat order using idle drones
        for f in fields_sorted:
            need = max(int(getattr(f, "drones_for_full_protection", 0)), 0) - len(final_alloc[f.id])
            if need <= 0:
                continue
            if not idle_drones:
                break
            # Sort idle by distance to the field
            idle_drones.sort(key=lambda d: self._dist_to_field(d, f))
            i = 0
            while need > 0 and i < len(idle_drones):
                d = idle_drones[i]
                final_alloc[f.id].add(d)
                i += 1
                need -= 1
            idle_drones = idle_drones[i:]

        # 6) Assign final groups
        drone_to_group = {}
        for f in fields_sorted:
            grp = f"protecting {f.id}"
            for d in final_alloc[f.id]:
                drone_to_group[d] = grp

        for d in components:
            environment.assign_group(d, drone_to_group.get(d, "idle"))