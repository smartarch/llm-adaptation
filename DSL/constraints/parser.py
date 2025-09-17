from lark import Lark
import os

_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), 'grammar.lark')

class ConstraintParser:
    def __init__(self):
        with open(_GRAMMAR_PATH, encoding='utf-8') as f:
            grammar = f.read()
        self.lark = Lark(grammar, parser='lalr', start='start')

    def parse(self, text):
        """
        Parse a DSL constraint string and return the Lark parse tree.
        """
        return self.lark.parse(text)

# Singleton instance for convenience
_default_parser = ConstraintParser()

def parse_constraint(text):
    """
    Parse a DSL constraint string using the default parser instance.
    """
    return _default_parser.parse(text)


if __name__ == "__main__":
    examples = [
        "once(`len(attack) >= 1`)",
        "forall field in `fields`: always(`len(protecting[field]) <= field.drones_for_full_protection`)",
        "scattered(3, `len(spawn_farmer) >= 2 or len(spawn_warrior) >= 2`)",
    ]
    for example in examples:
        print(f"Parsing: {example}")
        tree = parse_constraint(example)
        print(tree.pretty())
        print()
