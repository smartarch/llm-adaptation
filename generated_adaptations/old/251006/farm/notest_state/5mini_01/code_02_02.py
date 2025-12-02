from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to form group name for a field
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # Distance squared between drone and field center
        def dist2_to_field_center(drone, field):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0
            dx = getattr(loc, "x", 0) - cx
            dy = getattr(loc, "y", 0) - cy
            return dx * dx + dy * dy

        # Get threatened fields (threat_level > 0) sorted by descending threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threats: put everyone idle (if group exists)
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
            return

        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Create working sets
        all_drones = list(components)
        unassigned = set(all_drones)  # drones not yet assigned in this step
        assignments = {}  # drone -> group_name

        # Precompute current targets mapping for quick lookup
        drones_targeting_field = {}
        for field in threatened_fields:
            drones_targeting_field[field.id] = [d for d in all_drones if getattr(d, "target_id", None) == field.id]

        # Greedy fill: try to fully protect fields in descending threat order
        for field in threatened_fields:
            group_name = protecting_group(field.id)
            if group_name not in group_ids:
                # Can't assign to this field (group missing) -> skip it
                continue

            required_total = int(getattr(field, "drones_for_full_protection", 0) or 0)

            # Drones already targeting this field (prefer to keep them)
            already = [d for d in drones_targeting_field.get(field.id, []) if d in unassigned]
            # Also prefer currently protecting (state == "protecting") among those (they're included in target list)
            assigned_to_field = set(already)
            have = len(assigned_to_field)
            need = max(0, required_total - have)

            if need > 0:
                # Candidates to send: prioritize idle drones, then other drones by distance
                idle_candidates = [d for d in unassigned if getattr(d, "state", "") == "idle" and d not in assigned_to_field]
                idle_candidates.sort(key=lambda d: dist2_to_field_center(d, field))

                take_from_idle = idle_candidates[:need]
                for d in take_from_idle:
                    assigned_to_field.add(d)
                need -= len(take_from_idle)

            if need > 0:
                # Next prefer drones that are targeting lower-priority fields (i.e., currently targeting some other threatened field
                # or even non-threat field), sorted by distance to this field
                other_candidates = [d for d in unassigned if d not in assigned_to_field]
                other_candidates.sort(key=lambda d: dist2_to_field_center(d, field))
                take_from_others = other_candidates[:need]
                for d in take_from_others:
                    assigned_to_field.add(d)
                need -= len(take_from_others)

            # Assign the chosen drones to this field
            for d in assigned_to_field:
                assignments[d] = group_name
                if d in unassigned:
                    unassigned.remove(d)

        # After greedily trying to fully protect fields, assign remaining drones to help partially:
        # For each remaining drone, assign to the nearest threatened field that still hasn't reached its required_total.
        # Build current counts per field (from assignments and pre-existing targeting that we kept)
        field_assigned_counts = {}
        for field in threatened_fields:
            field_assigned_counts[field.id] = 0

        # Count already assigned ones
        for d, grp in assignments.items():
            # grp looks like "protecting Field_X"
            if grp.startswith("protecting "):
                fid = grp[len("protecting "):]
                if fid in field_assigned_counts:
                    field_assigned_counts[fid] += 1

        # Also include drones that were targeting fields but we didn't explicitly assign them above
        # (They are still in unassigned; we will now assign them)
        # For the purpose of counting, consider drones whose current target is a threatened field and that remain unassigned:
        for d in list(unassigned):
            tid = getattr(d, "target_id", None)
            if tid in field_assigned_counts:
                # Tentatively count them as currently heading there (we will actually assign according to best fit below)
                # But do not increment here; we'll prefer to keep them if beneficial by selecting nearest target below.
                pass

        # For each remaining drone, try to place it to a field that still needs drones (to reach full protection), nearest first
        remaining = list(unassigned)
        # For deterministic tie-breaking, sort by distance to the highest-threat field first (or by id)
        for d in remaining:
            # Find nearest field that still needs drones
            best_field = None
            best_dist = float("inf")
            for field in threatened_fields:
                fid = field.id
                required_total = int(getattr(field, "drones_for_full_protection", 0) or 0)
                current = field_assigned_counts.get(fid, 0)

                if current >= required_total:
                    continue  # field already full

                # distance
                d2 = dist2_to_field_center(d, field)
                if d2 < best_dist:
                    best_dist = d2
                    best_field = field

            if best_field:
                grp = protecting_group(best_field.id)
                if grp in group_ids:
                    assignments[d] = grp
                    field_assigned_counts[best_field.id] = field_assigned_counts.get(best_field.id, 0) + 1
                    unassigned.remove(d)

        # Any drones still unassigned: either all fields are full or no beneficial assignment -> set them to idle if possible,
        # otherwise assign to the most-threatened field's group (fallback)
        for d in list(unassigned):
            if "idle" in group_ids:
                assignments[d] = "idle"
            else:
                # fallback to highest-threat field group (should exist)
                top_group = protecting_group(threatened_fields[0].id)
                assignments[d] = top_group
            unassigned.remove(d)

        # Finally, perform the environment assignments
        for d, grp in assignments.items():
            environment.assign_group(d, grp)