from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _is_warrior(self, c):
        try:
            role = getattr(c, 'role', None) or getattr(c, 'type', None) or ''
            if 'warrior' in str(role).lower():
                return True
            if 'farmer' in str(role).lower():
                return False
        except Exception:
            pass
        try:
            if 'warrior' in str(c).lower():
                return True
            if 'farmer' in str(c).lower():
                return False
        except Exception:
            pass
        return False

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        warriors = [c for c in components if self._is_warrior(c)]
        farmers = [c for c in components if not self._is_warrior(c)]

        # Warriors always go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # If there are no warriors, send farmers to cave as last resort
        if not warriors and farmers:
            for f in farmers:
                environment.assign_group(f, "cave")
        else:
            # Farmers stay in village (farming / idle)
            for f in farmers:
                if "farm" in group_ids:
                    environment.assign_group(f, "farm")
                else:
                    # If no farm group, still send them to cave as backup attackers
                    environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        for c in components:
            environment.assign_group(c, "attack")