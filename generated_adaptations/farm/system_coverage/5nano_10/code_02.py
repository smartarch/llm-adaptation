from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Find the field with the highest threat_level (> 0)
        top_field = None
        for f in environment.fields:
            if getattr(f, "threat_level", 0) > 0:
                if top_field is None or f.threat_level > top_field.threat_level:
                    top_field = f

        # Prepare default assignment: all drones idle
        assignments = {comp: "idle" for comp in components}

        if top_field is not None:
            top_group = f"protecting {top_field.id}"
            # Only proceed if the group exists in group_ids
            have_top_group = top_group in group_ids

            # Drones currently protecting the top field
            currently_protecting = [
                c for c in components
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id
            ]
            already = len(currently_protecting)

            # Drones needed to fully protect the top field
            drones_needed = max(0, getattr(top_field, "drones_for_full_protection", 0) - already)

            if drones_needed > 0 and have_top_group:
                # Field center coordinates
                cx = (top_field.left + top_field.right) / 2.0
                cy = (top_field.top + top_field.bottom) / 2.0

                # Potential candidates to assign to the top field
                candidates = [
                    c for c in components
                    if not (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id)
                ]

                # Distance as squared distance to avoid sqrt
                def dist_sq(drone):
                    dx = getattr(drone.location, "x", 0) - cx
                    dy = getattr(drone.location, "y", 0) - cy
                    return dx*dx + dy*dy

                candidates.sort(key=dist_sq)

                # Assign the closest drones up to drones_needed
                for i in range(min(drones_needed, len(candidates))):
                    assignments[candidates[i]] = top_group

        # Apply assignments (respect valid group names)
        for comp, grp in assignments.items():
            if grp not in group_ids:
                # Fallback to idle if the target group name is not valid
                grp = "idle" if "idle" in group_ids else grp
            environment.assign_group(comp, grp)