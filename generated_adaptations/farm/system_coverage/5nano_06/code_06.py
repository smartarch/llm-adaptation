from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # 0 threats: idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat level (highest first)
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Map field_id -> group_name
        field_id_to_group = {f.id: f"protecting {f.id}" for f in fields_sorted}
        field_ids = set(field_id_to_group.keys())

        # 3) Initialize per-field drone sets, and collect already allocated drones
        field_to_drones = {f.id: set() for f in fields_sorted}
        assigned_to_field = set()  # drones already considered allocated to a field

        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if tid in field_ids and (st == "protecting" or st == "moving_to_field"):
                field_to_drones[tid].add(d)
                assigned_to_field.add(d)

        # 4) Build unassigned pool
        unassigned = [d for d in components if d not in assigned_to_field]

        # 5) Greedily fill fields in threat order
        for field in fields_sorted:
            current = field_to_drones[field.id]
            needed = max(int(getattr(field, "drones_for_full_protection", 0)), 0)
            if len(current) >= needed:
                continue

            need = needed - len(current)
            cx = (getattr(field, "left") + getattr(field, "right")) / 2.0
            cy = (getattr(field, "top") + getattr(field, "bottom")) / 2.0

            def dist(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                return math.hypot(dx, dy)

            if not unassigned:
                break  # no more drones to allocate

            unassigned.sort(key=dist)

            # Move closest drones to this field until we reach the needed count
            i = 0
            while len(current) < needed and i < len(unassigned):
                d = unassigned[i]
                current.add(d)
                assigned_to_field.add(d)
                i += 1

            # Update unassigned pool
            unassigned = unassigned[i:]

        # 6) Build final mapping and assign groups
        drone_to_group = {}
        for f in fields_sorted:
            grp = f"protecting {f.id}"
            for d in field_to_drones[f.id]:
                drone_to_group[d] = grp

        for d in components:
            if d in drone_to_group:
                environment.assign_group(d, drone_to_group[d])
            else:
                environment.assign_group(d, "idle")