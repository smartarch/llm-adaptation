from typing import List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones into groups:
        - "idle": drones not protecting any field
        - "protecting {field_id}": drones protecting a specific field (for fields with threat > 0)

        Strategy:
        - Consider all threatened fields (threat_level > 0), sort by threat descending.
        - Keep drones that are already protecting a field on that field's group (to preserve full protection).
        - Greedily attempt to fully protect as many fields as possible, starting from the highest threat.
        - Use the closest available drones to fill missing protection for each field.
        - After attempting full protection, allocate remaining drones to partially protect fields in threat order.
        - If no field is threatened, idle all drones.
        """
        # Gather threatened fields
        threatened_fields = [f for f in getattr(environment, 'fields', []) if getattr(f, 'threat_level', 0) > 0]
        if not threatened_fields:
            # Nothing to protect; idle all
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (high to low)
        threatened_fields.sort(key=lambda f: float(getattr(f, 'threat_level', 0)), reverse=True)

        # Precompute field centers
        centers = {}
        for f in threatened_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_field(drone, field_id):
            cx, cy = centers[field_id]
            loc = getattr(drone, 'location', None)
            if loc is None:
                return float('inf')
            dx = getattr(loc, 'x', 0.0) - cx
            dy = getattr(loc, 'y', 0.0) - cy
            return math.hypot(dx, dy)

        # Step 1: Keep current protectors in their respective groups
        current_protectors_by_field = {}
        for f in threatened_fields:
            current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == f.id]
            current_protectors_by_field[f.id] = current
            for d in current:
                environment.assign_group(d, f"protecting {f.id}")

        # Assigned set to avoid re-assigning drones that we’ve already placed
        assigned = set()
        for f in threatened_fields:
            for d in current_protectors_by_field.get(f.id, []):
                assigned.add(d)

        # Step 2: Fully protect as many fields as possible (greedy, by threat order)
        for f in threatened_fields:
            field_id = f.id
            current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == field_id]
            current_count = len(current)
            drones_for_full = getattr(f, 'drones_for_full_protection', 1)
            try:
                drones_for_full = int(drones_for_full)
            except (TypeError, ValueError):
                drones_for_full = 1
            needed = max(0, drones_for_full - current_count)

            if needed <= 0:
                continue

            # Candidates: drones not currently protecting this field and not yet assigned
            candidates = [d for d in components if d not in assigned and not (getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == field_id)]
            candidates.sort(key=lambda d: dist_to_field(d, field_id))

            for i in range(min(needed, len(candidates))):
                drone = candidates[i]
                environment.assign_group(drone, f"protecting {field_id}")
                assigned.add(drone)
                # Update current_count for this field for subsequent iterations
                current.append(drone)
                current_count += 1
                if current_count >= drones_for_full:
                    break

        # Step 3: Allocate any remaining drones to partially protect fields (to meet the "at least half" guideline)
        remaining = [d for d in components if d not in assigned]
        # Recompute current protectors for partial allocation
        for f in threatened_fields:
            field_id = f.id
            current = [d for d in components if getattr(d, 'state', None) == 'protecting' and getattr(d, 'target_id', None) == field_id]
            # If there are still drones available, try to add up to the field's drones_for_full_protection as a cap
            cap = getattr(f, 'drones_for_full_protection', 1)
            try:
                cap = int(cap)
            except (TypeError, ValueError):
                cap = 1
            if len(current) >= cap:
                continue

            # Sort remaining by distance to this field
            remaining.sort(key=lambda d: dist_to_field(d, field_id))

            for d in list(remaining):
                if len(current) >= cap:
                    break
                environment.assign_group(d, f"protecting {field_id}")
                assigned.add(d)
                remaining.remove(d)
                current.append(d)

        # Step 4: Any drones still unassigned -> idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")