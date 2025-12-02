from math import ceil
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Protect fields in descending order of threat_level:
        - Always fully protect the highest-threat field first (using closest drones).
        - Keep drones already protecting a field counted for that field.
        - Prefer drones already moving to the same field when selecting replacements.
        - After the highest-threat field is fully protected, try to fully protect other fields
          (in descending threat) using remaining drones.
        - Any drones left after allocations are assigned to 'idle'.
        """
        # Build list of fields that require protection (threat_level > 0), sorted by threat desc
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # Nothing to protect: make all drones idle
            for comp in components:
                environment.assign_group(comp, "idle")
            return

        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper: compute squared distance from a drone to field center
        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist2_to_field(comp, fcenter):
            loc = getattr(comp, "location")
            dx = loc.x - fcenter[0]
            dy = loc.y - fcenter[1]
            return dx*dx + dy*dy

        # Keep track of which drones we've already assigned
        assigned = set()
        # Using a list for available drones so we can remove items reliably
        available = list(components)

        # For each field in descending threat order, try to fully protect it
        for idx, field in enumerate(threat_fields):
            protect_group = f"protecting {field.id}"
            # Skip fields for which group is not valid
            if protect_group not in group_ids:
                continue

            fcenter = field_center(field)
            required_total = int(ceil(getattr(field, "drones_for_full_protection", 0)))

            # Count drones already protecting this field among available drones
            current_protectors = [
                c for c in available
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id
            ]
            current_count = len(current_protectors)
            needed = max(0, required_total - current_count)

            # If this is the highest-threat field (first in list), we must ensure it's fully protected
            # We will try to recruit closest available drones to reach required_total
            if needed > 0:
                # Candidate drones are those still available and not already counted as current_protectors
                candidates = [c for c in available if c not in current_protectors]

                # Sort candidates: prefer those already moving to this field, then by distance
                def cand_key(c):
                    state = getattr(c, "state", None)
                    target = getattr(c, "target_id", None)
                    # Prefer moving_to_field toward this field (best), then any moving_to_field, then others
                    if state == "moving_to_field" and target == field.id:
                        pref = 0
                    elif state == "moving_to_field":
                        pref = 1
                    else:
                        pref = 2
                    return (pref, dist2_to_field(c, fcenter))

                candidates.sort(key=cand_key)
                # Select up to needed drones (might be less if not enough available)
                selected = candidates[:needed]
            else:
                selected = []

            # Final list of drones to assign to this field
            to_assign = list(current_protectors) + list(selected)

            # Assign them and remove from available
            for d in to_assign:
                environment.assign_group(d, protect_group)
                assigned.add(d)
                # remove from available if present
                if d in available:
                    available.remove(d)

            # If we've assigned all drones, break early
            if not available:
                break

        # Any remaining drones are idle
        for d in available:
            environment.assign_group(d, "idle")
            assigned.add(d)

        # Sanity: ensure every component was assigned (if any remain unassigned, make them idle)
        for comp in components:
            if comp not in assigned:
                environment.assign_group(comp, "idle")