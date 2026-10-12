import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in threatened}

        assigned = set()

        # Phase: continuity and fill for each field in threat order
        for f in threatened:
            cx, cy = centers[f.id]
            # Current drones targeting this field
            current = [d for d in components if d.target_id == f.id and d.state in ("protecting", "moving_to_field")]
            # Keep the closest up to drones_for_full_protection
            current.sort(key=lambda d: (d.location.x - cx) ** 2 + (d.location.y - cy) ** 2)
            keep_num = min(len(current), int(getattr(f, "drones_for_full_protection", 0)))
            keepers = current[:keep_num]
            for d in keepers:
                environment.assign_group(d, f"protecting {f.id}")
            assigned.update(keepers)

            need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(keepers))
            if need <= 0:
                continue

            # Available drones not yet assigned
            candidates = [d for d in components if d not in assigned]
            candidates.sort(key=lambda d: (d.location.x - cx) ** 2 + (d.location.y - cy) ** 2)
            for d in candidates[:need]:
                environment.assign_group(d, f"protecting {f.id}")
                assigned.add(d)

        # Phase 3: idle remaining
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")