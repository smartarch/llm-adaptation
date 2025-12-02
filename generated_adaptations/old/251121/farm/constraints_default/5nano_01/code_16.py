from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with positive threat
        fields = getattr(environment, "fields", []) or []
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, move all drones to idle (or first valid idle group)
        if not threatening_fields:
            for d in components:
                target = "idle" if "idle" in group_ids else group_ids[0]
                environment.assign_group(d, target)
            return

        # Sort threatening fields by threat level (highest first)
        threatening_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatening_fields[0]

        # Center of the top field
        cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
        cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

        top_group = f"protecting {top_field.id}"

        # Helper to determine a drone's current group
        def current_group(d):
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                return f"protecting {d.target_id}"
            return "idle"

        # Compute how many drones currently protect the top field
        current_top = sum(1 for d in components if current_group(d) == top_group)
        required = int(getattr(top_field, "drones_for_full_protection", 1))
        need = max(0, required - current_top)

        moves = {}  # drone -> field_id to protect

        if need > 0:
            # Build candidate list with priorities to minimize disruption
            candidates = []
            for d in components:
                if current_group(d) == top_group:
                    continue  # already protecting top field
                cur = current_group(d)
                dist2 = float("inf")
                loc = getattr(d, "location", None)
                if loc is not None:
                    dx = getattr(loc, "x", 0) - cx
                    dy = getattr(loc, "y", 0) - cy
                    dist2 = dx*dx + dy*dy

                # Priority heuristic:
                # - Idle drones are best (low disruption)
                if cur == "idle":
                    priority = -1.0
                else:
                    # If protecting another field, prefer relocating those on the lowest-threat field
                    held_field = None
                    if cur.startswith("protecting "):
                        held_field = cur.split(" ", 1)[1]
                    thr = 0.0
                    if held_field is not None:
                        # Find threat level of the held field
                        for f in threatening_fields:
                            if f.id == held_field:
                                thr = getattr(f, "threat_level", 0.0)
                                break
                        # If not found among threatening_fields, look up in all fields
                        if thr == 0.0:
                            for f in fields:
                                if f.id == held_field:
                                    thr = getattr(f, "threat_level", 0.0)
                                    break
                    priority = thr  # lower threat -> higher priority to move
                candidates.append((priority, dist2, d))

            # Sort by priority then distance
            candidates.sort(key=lambda t: (t[0], t[1]))

            # Pick up to 'need' drones
            picked = [c[2] for c in candidates[:need]]

            for drone in picked:
                moves[drone] = top_field.id
                need -= 1
                if need <= 0:
                    break

        # Final assignment: assign each drone to its final group
        for d in components:
            if d in moves:
                target_group = f"protecting {moves[d]}"
            else:
                target_group = current_group(d)

            if target_group not in group_ids:
                target_group = "idle" if "idle" in group_ids else group_ids[0]

            environment.assign_group(d, target_group)