from typing import List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones into groups:
        - "idle" for idle drones
        - "protecting {field_id}" for drones protecting a specific field

        Strategy:
        1) Gather fields with threat_level > 0 and sort by threat (desc).
        2) Target the top field (highest threat) for full protection using the minimum number of drones
           required (drones_for_full_protection - currently_protecting_drones).
        3) Prefer drones that are idle or moving to other fields to fill the need.
        4) If not enough, reallocate from drones currently protecting other fields (least disruptive first).
        5) Assign all drones to a valid group (idle or protecting top field). Do not leave unassigned.
        """
        # Helper to compute distance between two points with x,y attributes
        def dist_to_point(p, q_center_x, q_center_y):
            px = getattr(p.location, 'x', 0.0)
            py = getattr(p.location, 'y', 0.0)
            dx = px - q_center_x
            dy = py - q_center_y
            return math.hypot(dx, dy)

        fields = list(getattr(environment, 'fields', []))
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If there are no threats, idle all drones
        if not threatened_fields:
            for d in components:
                group_id = "idle" if "idle" in group_ids else None
                if group_id is None:
                    # Fallback to a valid protecting group if present
                    group_id = next((g for g in group_ids if g.startswith("protecting")), "idle")
                environment.assign_group(d, group_id)
            return

        # Pick the top field by threat level
        top_field = max(threatened_fields, key=lambda f: getattr(f, 'threat_level', 0))
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            top_group = "idle"  # fallback if group not available

        # Center of the top field
        left = getattr(top_field, 'left', 0)
        right = getattr(top_field, 'right', 0)
        top = getattr(top_field, 'top', 0)
        bottom = getattr(top_field, 'bottom', 0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        drones_for_full = getattr(top_field, 'drones_for_full_protection', 0)
        protecting_drones = getattr(top_field, 'protecting_drones', 0)
        need = max(0, drones_for_full - protecting_drones)

        assignments = {}

        # Step 1: Keep current protectors for the top field
        for d in components:
            if getattr(d, 'state', '') == "protecting" and getattr(d, 'target_id', None) == top_field.id:
                assignments[d] = top_group

        # Step 2: If more drones are needed, allocate from available pool by proximity
        if need > 0:
            # Candidates: drones not currently protecting the top field
            candidates = [d for d in components if not (getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) == top_field.id)]

            # Sort candidates by distance to the top field center
            candidates.sort(key=lambda d: dist_to_point(d, center_x, center_y))

            allocated = 0
            for d in candidates:
                if allocated >= need:
                    break
                assignments[d] = top_group
                allocated += 1

            # If still not enough, consider reallocating from other fields (least disruptive first)
            if allocated < need:
                remaining = need - allocated
                others = [d for d in components if getattr(d, 'state', '') == 'protecting' and getattr(d, 'target_id', None) != top_field.id]
                others.sort(key=lambda d: dist_to_point(d, center_x, center_y))
                for d in others:
                    if allocated >= need:
                        break
                    assignments[d] = top_group
                    allocated += 1

        # Step 3: Assign remaining drones to idle (or fallback to a protecting group if needed)
        for d in components:
            if d in assignments:
                continue
            if "idle" in group_ids:
                assignments[d] = "idle"
            else:
                # Fallback to top_group if available; otherwise idle
                assignments[d] = top_group if top_group in group_ids else "idle"

        # Apply the assignments, ensuring group_ids validity
        for d in components:
            gid = assignments.get(d, "idle")
            if gid not in group_ids:
                gid = "idle" if "idle" in group_ids else top_group
            environment.assign_group(d, gid)