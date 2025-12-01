from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(fields, key=lambda f: f.threat_level)
        top_id = top_field.id

        # Count current protectors for the top field
        current_top_protectors = [
            c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_id
        ]
        current_top_count = len(current_top_protectors)

        # Drones needed to fully protect the top field
        need = max(0, top_field.drones_for_full_protection - current_top_count)

        # Center of the top field
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        # Free drones: those not currently protecting any field
        free_drones = [c for c in components if getattr(c, "state", None) != "protecting"]

        # Distance to field center for free drones
        def dist2(drone):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = loc.x - cx
            dy = loc.y - cy
            return dx * dx + dy * dy

        free_drones.sort(key=dist2)

        # Choose the nearest drones to fill the protection
        to_top_set_ids = set(id(c) for c in current_top_protectors)
        chosen = []
        for d in free_drones:
            if len(chosen) >= need:
                break
            chosen.append(d)
            to_top_set_ids.add(id(d))

        # Re-assign groups for all drones
        for c in components:
            if id(c) in to_top_set_ids:
                environment.assign_group(c, f"protecting {top_id}")
            else:
                # Preserve existing protection if drone was protecting some field
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                    environment.assign_group(c, f"protecting {c.target_id}")
                else:
                    environment.assign_group(c, "idle")