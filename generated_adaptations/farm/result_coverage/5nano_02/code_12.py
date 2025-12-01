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
        centers = {}
        for f in threatened:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Helper: squared distance from a drone to a field center
        def dist2_to_field(drone, field):
            cx, cy = centers[field.id]
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return dx*dx + dy*dy

        # Compute current counting of drones already targeting each field
        current_counts = {f.id: 0 for f in threatened}
        for d in components:
            if d.target_id is None:
                continue
            if any(f.id == d.target_id for f in threatened):
                if d.state in ("protecting", "moving_to_field"):
                    current_counts[d.target_id] = current_counts.get(d.target_id, 0) + 1

        assigned = set()

        # Phase 1: Continuity - keep closest drones currently targeting each field
        for f in threatened:
            need = max(0, f.drones_for_full_protection - current_counts.get(f.id, 0))
            if need <= 0:
                continue
            # Drones already targeting this field
            candidates = [d for d in components if d.target_id == f.id and d.state in ("protecting", "moving_to_field") and d not in assigned]
            candidates.sort(key=lambda d: dist2_to_field(d, f))
            for d in candidates[:need]:
                environment.assign_group(d, f"protecting {f.id}")
                assigned.add(d)
            # Any additional drones targeting this field but not kept will be idle later

        # Phase 2: Allocate remaining needed drones to threatened fields (non-overlapping)
        for f in threatened:
            need = max(0, f.drones_for_full_protection - sum(
                1 for d in components if d.target_id == f.id and d.state in ("protecting", "moving_to_field") and d not in assigned
            ))
            if need <= 0:
                continue
            available = [d for d in components if d not in assigned]
            if not available:
                break
            available.sort(key=lambda d: dist2_to_field(d, f))
            for d in available[:need]:
                environment.assign_group(d, f"protecting {f.id}")
                assigned.add(d)

        # Phase 3: Idle all drones not assigned
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")