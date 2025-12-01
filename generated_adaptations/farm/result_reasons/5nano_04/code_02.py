from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, keep all drones idle
        if not fields_with_threat:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (high to low), tie-breaker by drones_for_full_protection if available
        fields_sorted = sorted(
            fields_with_threat,
            key=lambda f: (-getattr(f, "threat_level", 0), -getattr(f, "drones_for_full_protection", 0))
        )

        # Helper: center of a field
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper: distance from a drone to a field center
        def dist_to_field(drone, field):
            cx, cy = field_center(field)
            dx = getattr(drone.location, "x", 0.0) - cx
            dy = getattr(drone.location, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Prepare assignment containers
        assigned_for_field = {fld.id: [] for fld in fields_sorted}
        assigned_set = set()

        # Stage 1: For each field in threat order, keep as many currently protecting drones as possible (up to drones_for_full_protection),
        # and fill the remainder with the closest available drones.
        for fld in fields_sorted:
            drones_needed = max(0, getattr(fld, "drones_for_full_protection", 0))
            if drones_needed == 0:
                continue

            # Drones currently protecting this field
            currently_protecting = [
                d for d in components
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fld.id
            ]

            # Keepers: those currently protecting, closest to the field center
            currently_protecting_sorted = sorted(
                currently_protecting, key=lambda d: dist_to_field(d, fld)
            )
            keepers = currently_protecting_sorted[:min(len(currently_protecting_sorted), drones_needed)]

            for d in keepers:
                assigned_for_field[fld.id].append(d)
                assigned_set.add(d)

            # If we still need more drones to reach full protection
            needed = drones_needed - len(keepers)
            if needed > 0:
                # Candidates are all drones not yet assigned to any field
                candidates = [d for d in components if d not in assigned_set]
                candidates_sorted = sorted(candidates, key=lambda d: dist_to_field(d, fld))
                for d in candidates_sorted[:needed]:
                    assigned_for_field[fld.id].append(d)
                    assigned_set.add(d)

        # Stage 2: Assign groups according to the plan
        for fld in fields_sorted:
            group_name = f"protecting {fld.id}"
            for d in assigned_for_field[fld.id]:
                environment.assign_group(d, group_name)

        # Stage 3: Any drone not assigned to a protecting group becomes idle
        for d in components:
            if d not in assigned_set:
                environment.assign_group(d, "idle")