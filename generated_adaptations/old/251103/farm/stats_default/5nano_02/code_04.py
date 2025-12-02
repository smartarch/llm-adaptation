import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle everyone
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper to compute field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Mapping of drone -> field_id it will protect (None means idle)
        assign_map = {}

        # Track which drones are already assigned to a field (start with what is already targeting)
        # We consider a drone committed to a field if its target_id matches that field.
        committed_to_field = {}
        for f in threat_fields:
            fid = f.id
            committed = [c for c in components if getattr(c, "target_id", None) == fid]
            committed_to_field[fid] = committed

        # Step 1: Ensure best field (first in list) is fully protected if possible
        best_field = threat_fields[0]
        best_id = best_field.id
        best_required = int(getattr(best_field, "drones_for_full_protection", 0))

        # Drones currently targeting best field
        current_commit_best = committed_to_field.get(best_id, [])
        if best_required <= 0:
            # No protection required for this field; just keep current commits (if any)
            for c in current_commit_best:
                assign_map[c] = best_id
        else:
            if len(current_commit_best) < best_required:
                need = best_required - len(current_commit_best)
                # Candidates: drones not currently targeting best_field
                cx, cy = field_center(best_field)

                def dist2_to_best(d):
                    dx = getattr(d.location, "x", 0.0) - cx
                    dy = getattr(d.location, "y", 0.0) - cy
                    return dx*dx + dy*dy

                candidates = [c for c in components if getattr(c, "target_id", None) != best_id]
                candidates.sort(key=dist2_to_best)

                to_take = candidates[:need]
                for c in to_take:
                    assign_map[c] = best_id

            # Ensure all currently committed to best_field are assigned to protect it
            for c in current_commit_best:
                assign_map[c] = best_id

        # Step 2: Allocate remaining field protection (second, third, ...) in order of threat
        # Build a set of fields already allocated
        allocated_field_ids = set([best_id])

        for field in threat_fields[1:]:
            fid = field.id
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                # No full protection required; skip but keep any current commits if present
                current_committed = committed_to_field.get(fid, [])
                for c in current_committed:
                    assign_map[c] = fid
                allocated_field_ids.add(fid)
                continue

            current_committed = committed_to_field.get(fid, [])
            if len(current_committed) >= required:
                # Field already fully protected (based on current state)
                for c in current_committed:
                    assign_map[c] = fid
                allocated_field_ids.add(fid)
                continue

            need = required - len(current_committed)
            # Candidates: drones not already assigned to a different field in this tick
            already_assigned = set(assign_map.keys())

            def dist2_to_field(d, field_center):
                cx, cy = field_center
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                return dx*dx + dy*dy

            cx, cy = field_center(field)
            # Prefer drones not currently assigned; among them pick closest to the field
            available = [c for c in components if c not in already_assigned and c not in current_committed]
            available.sort(key=lambda d: dist2_to_field(d, (cx, cy)))

            take = available[:need]
            for c in take:
                assign_map[c] = fid

            # Also ensure current commits stay assigned
            for c in current_committed:
                assign_map[c] = fid

            allocated_field_ids.add(fid)

        # Step 3: Assign groups for all drones based on assign_map
        # Drones not in assign_map are idle
        for c in components:
            if c in assign_map:
                field_id = assign_map[c]
                environment.assign_group(c, f"protecting {field_id}")
            else:
                environment.assign_group(c, "idle")