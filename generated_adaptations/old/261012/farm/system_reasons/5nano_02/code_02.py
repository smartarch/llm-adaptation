from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Keep a simple memory of last group per drone (keyed by Python id of the drone object)
        self._last_group = {}

    def _record_assignment(self, drone_key, group):
        # drone_key is the id(drone) used in this strategy
        self._last_group[drone_key] = group

    def _previous_group(self, drone_key):
        return self._last_group.get(drone_key, None)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with non-zero threat level
        fields = []
        for f in getattr(environment, "fields", []) or []:
            if getattr(f, "threat_level", 0) > 0:
                fields.append(f)

        # If no threat, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
                self._record_assignment(id(d), "idle")
            return

        # Sort fields by threat level descending (most threatened first)
        fields_sorted = sorted(fields, key=lambda fld: fld.threat_level, reverse=True)

        # Helper to compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Allocate drones to fields in priority order
        allocated = set()  # keys are id(drone)
        allocations = {}   # field_id -> list of drone objects

        for field in fields_sorted:
            need = int(getattr(field, "drones_for_full_protection", 0))
            if need <= 0:
                continue

            # Build list of currently unallocated drones
            available = [d for d in components if id(d) not in allocated]
            if not available:
                break

            center = center_of(field)
            field_group = f"protecting {field.id}"

            # Distances to field center
            def dist_to_field(drone):
                loc = getattr(drone, "location", None)
                if loc is None:
                    return float('inf')
                dx = getattr(loc, "x", 0.0) - center[0]
                dy = getattr(loc, "y", 0.0) - center[1]
                return (dx*dx + dy*dy) ** 0.5

            # Prefer drones that were previously protecting this field
            previously_protecting = [
                d for d in available if self._previous_group(id(d)) == field_group
            ]

            chosen = []
            if previously_protecting:
                # Sort those by proximity and take as many as possible up to 'need'
                previously_sorted = sorted(previously_protecting, key=dist_to_field)
                for d in previously_sorted:
                    if len(chosen) < need:
                        chosen.append(d)
                        allocated.add(id(d))

            # Fill the remaining slots with the closest remaining drones
            if len(chosen) < need:
                remaining = [d for d in available if id(d) not in allocated]
                remaining_sorted = sorted(remaining, key=dist_to_field)
                for d in remaining_sorted:
                    if len(chosen) < need:
                        chosen.append(d)
                        allocated.add(id(d))
                    else:
                        break

            if chosen:
                allocations[field.id] = chosen

        # Build target group per drone
        drone_to_group = {}
        for field_id, drones in allocations.items():
            gid = f"protecting {field_id}"
            for d in drones:
                drone_to_group[id(d)] = gid

        # All non-assigned drones go to idle
        for d in components:
            if id(d) not in drone_to_group:
                drone_to_group[id(d)] = "idle"

        # Apply groups and remember the assignments
        for d in components:
            gid = drone_to_group[id(d)]
            environment.assign_group(d, gid)
            self._record_assignment(id(d), gid)