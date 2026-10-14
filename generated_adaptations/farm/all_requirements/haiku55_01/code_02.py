import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    # Distance-units bonus that keeps drones on the field they already protect
    # (applied to all fields except the most threatened one).
    STICKY_BONUS = 5.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _distance(self, drone, field):
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _ranked_candidates(self, candidates, field, is_top):
        """Order candidate drones: nearest first; sticky bonus for non-top fields."""
        def key(d):
            score = self._distance(d, field)
            if not is_top and d.target_id == field.id:
                score -= self.STICKY_BONUS
            return score
        return sorted(candidates, key=key)

    def assign_drones(self, components, environment, group_ids, step: int):
        valid = set(group_ids)

        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        unassigned = list(components)
        allocation = {f.id: [] for f in fields}
        need = {f.id: max(1, int(f.drones_for_full_protection)) for f in fields}

        # Pass 1: full protection, in threat order, no overprotection.
        for rank, field in enumerate(fields):
            is_top = (rank == 0)
            n = need[field.id]
            if len(unassigned) < n and not is_top:
                # Cannot fully protect this field; leave it for the leftover pass.
                continue
            ranked = self._ranked_candidates(unassigned, field, is_top)
            chosen = ranked[:n]  # top field takes all available if too few drones
            allocation[field.id].extend(chosen)
            for d in chosen:
                unassigned.remove(d)

        # Pass 2: leftover drones give partial protection to the most threatened
        # fields that are still below their full requirement, never exceeding it.
        for rank, field in enumerate(fields):
            if not unassigned:
                break
            deficit = need[field.id] - len(allocation[field.id])
            if deficit <= 0:
                continue
            ranked = self._ranked_candidates(unassigned, field, rank == 0)
            chosen = ranked[:deficit]
            allocation[field.id].extend(chosen)
            for d in chosen:
                unassigned.remove(d)

        # Apply group assignments; each drone is assigned exactly once.
        for field in fields:
            group = f"protecting {field.id}"
            target_group = group if group in valid else "idle"
            for d in allocation[field.id]:
                environment.assign_group(d, target_group)

        for d in unassigned:
            environment.assign_group(d, "idle")