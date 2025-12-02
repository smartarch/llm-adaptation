from typing import List
import math
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

        # Choose the top-threat field (tie-break by fewer current defenders, handled implicitly)
        top_field = max(threat_fields, key=lambda f: getattr(f, "threat_level", 0))

        # Number of drones needed for full protection (default to 1 if not provided)
        required = int(getattr(top_field, "drones_for_full_protection", 1))

        # Helper to identify drones heading to top_field (protecting or moving_to_field)
        def heading_to_top(d) -> bool:
            if getattr(d, "target_id", None) is None:
                return False
            if d.state in ("protecting", "moving_to_field") and getattr(d, "target_id", None) == top_field.id:
                return True
            return False

        # Current drones effectively protecting top_field (including those en route)
        current_top = [d for d in components if heading_to_top(d)]
        current_top_count = len(current_top)

        # Drones that are not currently heading to top_field
        current_top_ids = set(id(d) for d in current_top)

        if current_top_count < required:
            to_select = required - current_top_count

            # Compute center of the top field for distance calculations
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            # Build candidate drones excluding those already heading to top_field
            candidates = []
            for d in components:
                if id(d) in current_top_ids:
                    continue
                # Distance to top field center
                lx = getattr(d.location, "x", 0)
                ly = getattr(d.location, "y", 0)
                dx = lx - cx
                dy = ly - cy
                dist2 = dx*dx + dy*dy
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])

            # Select the nearest drones to fill the gap
            selected = [d for _, d in candidates[:to_select]]
            for d in selected:
                environment.assign_group(d, f"protecting {top_field.id}")

            # Update the set of top-field drones after assignment
            top_group_ids = set(id(d) for d in current_top)
            top_group_ids.update(id(d) for d in selected)
        else:
            # No more drones needed for top_field; keep as is
            top_group_ids = set(id(d) for d in current_top)

        # Ensure all drones are assigned to some group:
        # - Drones in top field group -> protecting top_field
        # - Drones heading to other fields keep their respective groups
        # - Idle drones -> idle
        for d in components:
            did = id(d)
            if did in top_group_ids:
                environment.assign_group(d, f"protecting {top_field.id}")
            else:
                # If drone is protecting or moving toward another field, preserve that protection
                target = getattr(d, "target_id", None)
                if d.state in ("protecting", "moving_to_field") and target is not None:
                    environment.assign_group(d, f"protecting {target}")
                else:
                    environment.assign_group(d, "idle")