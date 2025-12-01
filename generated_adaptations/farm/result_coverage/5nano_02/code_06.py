import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threats: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort by threat level (high to low)
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # Precompute field centers for distance calculations
        centers = {}
        for f in threatened:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Determine current targeting counts for each threatened field
        current_counts = {f.id: 0 for f in threatened}
        for d in components:
            if d.target_id is not None:
                # If the targeted field is in our threatened list, count it
                if any(f.id == d.target_id for f in threatened):
                    current_counts[d.target_id] = current_counts.get(d.target_id, 0) + 1

        # We will assign drones to fields in order, ensuring non-overlap
        picked = set()  # drones already allocated in this step
        # Helper to compute squared distance to a field center
        def dist2_to_field_center(drone, field_id):
            cx, cy = centers[field_id]
            loc = drone.location
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # Final assignment of drones to fields
        for f in threatened:
            center_id = f.id
            need = max(0, f.drones_for_full_protection - current_counts.get(center_id, 0))

            if need <= 0:
                # Ensure any drones currently targeting this field end up in the correct group
                for d in components:
                    if d.target_id == center_id:
                        environment.assign_group(d, f"protecting {center_id}")
                continue

            # Candidates: drones not yet picked
            candidates = [d for d in components if d not in picked]
            # Sort by proximity to this field's center
            candidates.sort(key=lambda d: dist2_to_field_center(d, center_id))
            chosen = candidates[:need]

            for d in chosen:
                environment.assign_group(d, f"protecting {center_id}")
            picked.update(chosen)

        # Any drones not allocated to a field become idle
        for d in components:
            if d not in picked:
                environment.assign_group(d, "idle")