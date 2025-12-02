from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        components: list of drone components
        environment: environment providing fields and assign_group
        group_ids: list of all valid group names (unused directly, but available)
        step: current timestep (unused in this strategy but kept for compatibility)
        """
        # Gather fields with threat > 0
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the top-threat field (tie-break by threat level)
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # Number of drones needed for full protection (default to 1 if not provided)
        required = int(getattr(top_field, "drones_for_full_protection", 1))

        # Drones currently heading to or protecting the top_field
        current_top = []
        for d in components:
            if d.state in ("protecting", "moving_to_field") and getattr(d, "target_id", None) == top_field.id:
                current_top.append(d)

        current_top_set = set(current_top)

        # If not enough drones, pick nearest available drones to fill the gap
        if len(current_top) < required:
            need = required - len(current_top)

            # Center of the top field for distance calculations
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            candidates = []
            for d in components:
                if id(d) in {id(x) for x in current_top}:
                    continue
                lx = getattr(d.location, "x", 0)
                ly = getattr(d.location, "y", 0)
                dx = lx - cx
                dy = ly - cy
                dist2 = dx*dx + dy*dy
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])
            selected = [d for _, d in candidates[:need]]
        else:
            selected = []

        top_group_ids = {id(d) for d in current_top}
        top_group_ids.update(id(d) for d in selected)

        # Final assignment: exactly one environment.assign_group call per drone
        for d in components:
            if id(d) in top_group_ids:
                environment.assign_group(d, f"protecting {top_field.id}")
            else:
                t = getattr(d, "target_id", None)
                st = getattr(d, "state", "")
                if st in ("protecting", "moving_to_field") and t is not None:
                    environment.assign_group(d, f"protecting {t}")
                else:
                    environment.assign_group(d, "idle")