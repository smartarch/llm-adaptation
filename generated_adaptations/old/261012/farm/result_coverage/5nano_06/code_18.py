from typing import List
import math

# Import the base class to derive from
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Stable, idle-only deficit-fill strategy:
        - Identify all threatened fields (threat_level > 0).
        - For each field (sorted by threat level desc), compute deficit = max(0, drones_for_full_protection - current_protecting).
        - Use closest idle drones to fill deficits, without taking drones away from fields that are protecting.
        - After processing, ensure all drones not in a protecting group become idle.
        """
        # Helper: center of a field
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance from a drone to a field center
        def dist_to_field(drone, field):
            cx, cy = field_center(field)
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]

        if not threatened_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (high to low)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        field_ids = {f.id for f in threatened_fields}

        # Current protection counts per field
        current_by_field = {fid: 0 for fid in field_ids}
        for d in components:
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_ids:
                    current_by_field[tid] += 1

        # Full protection requirements per field
        full_by_field = {fid: int(getattr(next((f for f in threatened_fields if f.id == fid), None), "drones_for_full_protection", 0))
                         for fid in field_ids}

        # Deficits per field
        deficits = {fid: max(0, full_by_field.get(fid, 0) - current_by_field.get(fid, 0)) for fid in field_ids}

        # Idle drones: not currently protecting
        idle = [d for d in components if getattr(d, "state", "") != "protecting"]

        assigned = set()

        # Process fields in threat order, fill deficits with closest idle drones
        for f in threatened_fields:
            fid = f.id
            need = deficits.get(fid, 0)
            if need <= 0:
                # Ensure current protectors remain in their group
                for d in components:
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, f"protecting {fid}")
                        assigned.add(d)
                continue

            if not idle:
                continue  # no idle drones left to fill this field

            cx, cy = field_center(f)
            # Sort idle drones by distance to this field
            idle.sort(key=lambda d: math.hypot(getattr(d.location, "x", 0.0) - cx,
                                                getattr(d.location, "y", 0.0) - cy))
            take = min(need, len(idle))
            for i in range(take):
                d = idle.pop(0)
                environment.assign_group(d, f"protecting {fid}")
                assigned.add(d)
                current_by_field[fid] = current_by_field.get(fid, 0) + 1
                need -= 1

            # Update deficits for this field
            deficits[fid] = max(0, full_by_field.get(fid, 0) - current_by_field.get(fid, 0))

        # Re-affirm protecting drones stay in their groups
        for d in components:
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_ids:
                    environment.assign_group(d, f"protecting {tid}")
                    assigned.add(d)

        # Finalize: any unassigned drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")