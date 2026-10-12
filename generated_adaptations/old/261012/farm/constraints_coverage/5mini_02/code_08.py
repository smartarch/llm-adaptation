from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    """
    Always fully protect the highest-threat field using the closest drones, keep existing protectors,
    then assign additional drones to other threatened fields until at least half of drones are protecting (if possible).
    Every component is explicitly assigned each step.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name if name in group_ids else "idle"

        # Threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened_fields:
            idle = valid_group("idle")
            for c in components:
                environment.assign_group(c, idle)
            return

        # Distance helpers (field center)
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field(comp, field):
            cx, cy = field_center(field)
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        # Current protectors and movers by field id
        protecting_by_field = {}
        moving_by_field = {}
        for comp in components:
            state = getattr(comp, "state", "")
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target is not None:
                protecting_by_field.setdefault(target, []).append(comp)
            if state == "moving_to_field" and target is not None:
                moving_by_field.setdefault(target, []).append(comp)

        total = len(components)
        half_required = ceil(total / 2)

        # Top field first
        top_field = max(threatened_fields, key=lambda f: f.threat_level)
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        selected_assignment = {}  # comp -> field_id
        available = set(components)

        # Fill a field up to required: keep protectors, then movers, then closest available
        def fill_field(field, required):
            # keep protectors
            kept = [c for c in protecting_by_field.get(field.id, []) if c in available]
            chosen = list(kept)
            # add movers
            movers = [c for c in moving_by_field.get(field.id, []) if c in available and c not in chosen]
            need = max(0, required - len(chosen))
            if need > 0:
                chosen.extend(movers[:need])
            # add nearest available if still needed
            if len(chosen) < required:
                need = required - len(chosen)
                candidates = [c for c in available if c not in chosen]
                candidates.sort(key=lambda c: distance_to_field(c, field))
                chosen.extend(candidates[:need])
            # assign chosen
            for c in chosen:
                selected_assignment[c] = field.id
                if c in available:
                    available.remove(c)

        # Ensure top field is fully protected
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        fill_field(top_field, required_top)

        # If still fewer than half protecting, try to fill other fields until half reached
        if len(selected_assignment) < half_required:
            for f in other_fields:
                if len(selected_assignment) >= half_required:
                    break
                if not available:
                    break
                req = int(getattr(f, "drones_for_full_protection", 0))
                fill_field(f, req)

        # As a last effort, keep remaining current protectors on threatened fields if still under half
        if len(selected_assignment) < half_required and available:
            for c in list(available):
                if len(selected_assignment) >= half_required:
                    break
                if getattr(c, "state", "") == "protecting":
                    tgt = getattr(c, "target_id", None)
                    if tgt and any(f.id == tgt for f in threatened_fields):
                        selected_assignment[c] = tgt
                        available.remove(c)

        # Prepare group names
        idle_group = valid_group("idle")
        protecting_group_cache = {f.id: valid_group(f"protecting {f.id}") for f in threatened_fields}

        # Assign groups for all components explicitly
        for c in components:
            if c in selected_assignment:
                gid = protecting_group_cache.get(selected_assignment[c], idle_group)
                environment.assign_group(c, gid)
            else:
                environment.assign_group(c, idle_group)