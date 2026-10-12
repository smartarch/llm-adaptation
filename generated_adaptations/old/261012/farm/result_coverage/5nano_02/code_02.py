import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Determine the field with the highest threat (threat > 0)
        top_field = None
        max_threat = -1.0
        for f in environment.fields:
            if getattr(f, "threat_level", 0.0) > max_threat:
                max_threat = f.threat_level
                top_field = f

        # If no threatened field, idle all drones
        if top_field is None or max_threat <= 0:
            for c in components:
                environment.assign_group(c, "idle")
            return

        top_group = f"protecting {top_field.id}"

        # Compute field center
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Drones currently assigned to this field (by target_id)
        assigned_to_top = [c for c in components if c.target_id == top_field.id]

        # Helper: squared distance to the field center
        def dist2_to_top(d):
            loc = d.location
            dx = loc.x - cx
            dy = loc.y - cy
            return dx*dx + dy*dy

        # If there are more drones assigned to the top field than needed,
        # keep the closest drones and move extras to idle.
        if len(assigned_to_top) > top_field.drones_for_full_protection:
            assigned_to_top.sort(key=dist2_to_top)
            keepers = assigned_to_top[:top_field.drones_for_full_protection]
            extras = assigned_to_top[top_field.drones_for_full_protection:]
            for ex in extras:
                environment.assign_group(ex, "idle")
        else:
            keepers = assigned_to_top

        # Ensure all keepers are assigned to the top protection group
        for c in keepers:
            environment.assign_group(c, top_group)

        # Drones still needed to reach full protection
        needed = max(0, top_field.drones_for_full_protection - len(keepers))

        # Candidates: all drones not currently kept for top protection
        candidates = [c for c in components if c not in keepers]

        # Sort candidates by distance to the top field center
        candidates.sort(key=lambda d: (d.location.x - cx) ** 2 + (d.location.y - cy) ** 2)

        # Promote the closest 'needed' drones to top protection
        for c in candidates[:needed]:
            environment.assign_group(c, top_group)

        # Remaining drones go idle
        for c in candidates[needed:]:
            environment.assign_group(c, "idle")