from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper: squared distance from a component to a point
        def dist2(comp, px, py):
            dx = (comp.location.x - px)
            dy = (comp.location.y - py)
            return dx * dx + dy * dy

        # Build map of valid protecting group names for quick check
        protecting_group_for_field = {}
        fields_with_threat = []
        for field in environment.fields:
            if field.threat_level > 0:
                grp = f"protecting {field.id}"
                if grp in group_ids:
                    protecting_group_for_field[field.id] = grp
                else:
                    # group missing in provided group_ids; we'll treat as unavailable
                    protecting_group_for_field[field.id] = None
                fields_with_threat.append(field)

        # Select highest-threat field (tie-breaker by id for determinism)
        top_field = None
        if fields_with_threat:
            # Sort by threat level desc, then by id to break ties
            fields_with_threat.sort(key=lambda f: (-f.threat_level, str(f.id)))
            top_field = fields_with_threat[0]

        # Prepare assignments: component -> group_id
        assignments = {}

        # First: preserve existing protections (drones that are currently protecting)
        # Keep them protecting their current target (if that target has a valid group), else assign idle
        for comp in components:
            if comp.state == "protecting" and comp.target_id is not None:
                grp_name = f"protecting {comp.target_id}"
                if grp_name in group_ids:
                    assignments[comp] = grp_name
                else:
                    # protecting group not available in group_ids: fallback to idle
                    assignments[comp] = "idle"

        # If there's a top field to protect, ensure it is fully protected by adding closest available drones
        if top_field is not None:
            top_grp = f"protecting {top_field.id}"
            # If the protecting group for the top field doesn't exist, we cannot assign to it; skip
            if top_grp in group_ids:
                required = int(top_field.drones_for_full_protection)
                # Count already assigned protectors for this field
                current_protectors = [c for c, g in assignments.items() if g == top_grp]
                num_current = len(current_protectors)

                if num_current < required:
                    # Candidates are drones not currently assigned to protect other fields
                    # (i.e., components not in assignments or assigned to idle)
                    candidates = []
                    cx, cy = field_center(top_field)
                    for comp in components:
                        # Skip those already assigned to protect any field
                        if comp in assignments and assignments[comp] != "idle":
                            # already protecting some field; do not reassign them away
                            continue
                        # valid candidate
                        candidates.append((dist2(comp, cx, cy), comp))
                    # sort candidates by distance ascending
                    candidates.sort(key=lambda x: x[0])
                    needed = required - num_current
                    for _, comp in candidates[:needed]:
                        assignments[comp] = top_grp

        # Finally assign everyone not yet assigned to idle (must be a valid group)
        for comp in components:
            if comp not in assignments:
                # default to idle if available, otherwise pick any valid group (fallback)
                if "idle" in group_ids:
                    assignments[comp] = "idle"
                else:
                    # fallback: choose first group id
                    assignments[comp] = group_ids[0] if group_ids else "idle"

        # Apply assignments using environment.assign_group
        for comp, grp in assignments.items():
            # ensure group exists; if not, fall back to idle if possible
            if grp not in group_ids:
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else grp)
            environment.assign_group(comp, grp)