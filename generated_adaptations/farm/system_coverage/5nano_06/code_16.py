from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center(self, f):
        return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

    def _dist(self, d, center):
        loc = getattr(d, "location", None)
        if loc is None:
            return float('inf')
        x = getattr(loc, "x", 0.0)
        y = getattr(loc, "y", 0.0)
        return math.hypot(x - center[0], y - center[1])

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat
        fields = [fld for fld in environment.fields if getattr(fld, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by threat level (highest first), tie-breaking by protection need
        fields_sorted = sorted(
            fields,
            key=lambda f: (getattr(f, "threat_level", 0), getattr(f, "drones_for_full_protection", 0)),
            reverse=True
        )
        field_ids = [f.id for f in fields_sorted]
        id_to_index = {fid: i for i, fid in enumerate(field_ids)}

        # 3) Initial allocations: drones currently protecting or moving toward any field
        final_alloc = {f.id: set() for f in fields_sorted}
        allocated = set()
        for d in components:
            st = getattr(d, "state", "")
            tid = getattr(d, "target_id", None)
            if tid in field_ids and st in ("protecting", "moving_to_field"):
                final_alloc[tid].add(d)
                allocated.add(d)

        # 4) Allocate for each field in threat order
        for i, f in enumerate(fields_sorted):
            current = final_alloc[f.id]
            needed = max(int(getattr(f, "drones_for_full_protection", 0)), 0) - len(current)
            if needed <= 0:
                continue

            # 4a) Idle candidates first (closest to the field)
            center = self._center(f)
            idle_candidates = [
                d for d in components
                if d not in allocated and getattr(d, "state", "") == "idle" and getattr(d, "target_id", None) is None
            ]
            idle_candidates.sort(key=lambda d: self._dist(d, center))

            # 4b) Then consider drones currently protecting lower-threat fields (closest first)
            downward_candidates = [
                d for d in components
                if d not in allocated and getattr(d, "target_id", None) in field_ids and id_to_index.get(getattr(d, "target_id"), 9999) > i
            ]
            downward_candidates.sort(key=lambda d: self._dist(d, center))

            # 4c) Fill using idle first, then lower-field drones
            for pool in (idle_candidates, downward_candidates):
                if needed <= 0:
                    break
                for d in pool:
                    if d in allocated:
                        continue
                    final_alloc[f.id].add(d)
                    allocated.add(d)
                    needed -= 1
                    if needed <= 0:
                        break

        # 5) Assign final groups
        drone_to_group = {}
        for f in fields_sorted:
            grp = f"protecting {f.id}"
            for d in final_alloc[f.id]:
                drone_to_group[d] = grp

        for d in components:
            environment.assign_group(d, drone_to_group.get(d, "idle"))