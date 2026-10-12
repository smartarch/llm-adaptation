import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in threatened}

        # Phase 1: Continuity - keep closest drones currently targeting each field
        assigned = set()
        needs = {}
        for f in threatened:
            current = [
                d for d in components
                if d.target_id == f.id and d.state in ("protecting", "moving_to_field")
            ]
            # Current need to reach full protection
            current.sort(key=lambda d: (d.location.x - centers[f.id][0]) ** 2 + (d.location.y - centers[f.id][1]) ** 2)
            current_need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(current))
            needs[f.id] = current_need

            # Keep up to current_need drones for this field
            keep_num = min(len(current), int(getattr(f, "drones_for_full_protection", 0)))
            keepers = current[:keep_num]
            for d in keepers:
                environment.assign_group(d, f"protecting {f.id}")
            assigned.update(keepers)

            # Drones targeting this field but not kept go idle
            for d in current[keep_num:]:
                environment.assign_group(d, "idle")

        # Phase 2: Allocate remaining needs with closest available drones
        # Iterate until no field needs more drones or we run out of drones
        while True:
            # Recompute which fields still need protection
            need_fields = []
            for f in threatened:
                current_count = sum(
                    1 for d in components if d.target_id == f.id and d.state in ("protecting", "moving_to_field")
                )
                need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_count)
                needs[f.id] = need
                if need > 0:
                    need_fields.append(f)

            if not need_fields:
                break  # all protected or no drones left

            # Choose the field with highest threat; tie-break by smaller need
            need_fields.sort(key=lambda ff: (ff.threat_level, -needs[ff.id]), reverse=True)
            f = need_fields[0]
            need = needs[f.id]
            if need <= 0:
                # Shouldn't happen, but guard anyway
                del needs[f.id]
                continue

            # Find closest available drone
            available = [d for d in components if d not in assigned]
            if not available:
                break

            cx, cy = centers[f.id]
            available.sort(key=lambda d: (d.location.x - cx) ** 2 + (d.location.y - cy) ** 2)
            for d in available[:need]:
                environment.assign_group(d, f"protecting {f.id}")
                assigned.add(d)

        # Phase 3: Idle remaining drones
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")