from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        top_field = fields_sorted[0]

        # 3) Build current allocations for each field (protecting or moving_to_field)
        current_alloc = {f.id: set() for f in fields_sorted}
        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if tid in field_ids and st in ("protecting", "moving_to_field"):
                current_alloc[tid].add(d)

        # 4) Build pool of idle drones (prefer closest to fields when assigning)
        # We only pull from truly idle drones to minimize churn
        idle_drones = [d for d in components if getattr(d, "state", "") == "idle" and getattr(d, "target_id", None) is None]

        # Helper: field center
        def center_of(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(d, f):
            loc = getattr(d, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = center_of(f)
            x = getattr(loc, "x", 0.0)
            y = getattr(loc, "y", 0.0)
            return math.hypot(x - cx, y - cy)

        # 5) Greedily fill fields in threat order using idle drones
        for f in fields_sorted:
            needed = max(int(getattr(f, "drones_for_full_protection", 0)), 0) - len(current_alloc[f.id])
            if needed <= 0:
                continue
            if not idle_drones:
                break  # no more idle drones to allocate

            # Sort idle drones by distance to this field
            idle_drones.sort(key=lambda d: dist_to_field(d, f))

            i = 0
            while needed > 0 and i < len(idle_drones):
                d = idle_drones[i]
                current_alloc[f.id].add(d)
                i += 1
                needed -= 1

            # Remove allocated drones from idle pool
            idle_drones = idle_drones[i:]

        # 6) Build final mapping and assign groups
        drone_to_group = {}
        for f in fields_sorted:
            grp = f"protecting {f.id}"
            for d in current_alloc[f.id]:
                drone_to_group[d] = grp

        for d in components:
            environment.assign_group(d, drone_to_group.get(d, "idle"))