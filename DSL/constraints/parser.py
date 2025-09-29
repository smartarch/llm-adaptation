import os
from lark import Lark, Transformer, v_args

from DSL.constraints.evaluation import PyExpr, TemporalHistory, TemporalWithin, Implies, ForAll


_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), 'grammar-simple.lark')

class ConstraintParser:
    def __init__(self):
        with open(_GRAMMAR_PATH, encoding='utf-8') as f:
            grammar = f.read()
        self.lark = Lark(grammar, parser='lalr', start='start')

    def parse(self, text: str):
        """Parse a DSL constraint string and return the Lark parse tree."""
        return self.lark.parse(text)


@v_args(inline=True)
class ConstraintASTTransformer(Transformer):
    """AST transformer"""

    def start(self, child):
        # Unwrap the top-level 'start' rule for a cleaner AST
        return child
    
    def formula(self, child):
        # Unwrap the 'formula' rule
        return child

    def temporal(self, child):
        # Unwrap the 'temporal' rule (for all temporal operators)
        return child

    def py_expr(self, token):
        # Strip backticks, unescape \`
        code = str(token)[1:-1].replace('\\`', '`')
        return PyExpr(code)

    def num_arg(self, child):
        # Unwrap the 'num_arg' rule
        return child

    def within_call(self, min_occurrences, window, expr):
        return TemporalWithin(min_occurrences, window, expr)

    def scattered_call(self, min_occurrences, expr):
        # scattered(n, expr) => within(n, MAX, expr)
        return TemporalWithin(min_occurrences, PyExpr("MAX"), expr)

    def consequent_call(self, window, expr):
        # consequent(t, expr) => within(t, t, expr)
        return TemporalWithin(window, window, expr)

    def always_call(self, expr):
        # always(expr) => within(MAX, MAX, expr)
        return TemporalWithin(PyExpr("MAX"), PyExpr("MAX"), expr)

    def once_call(self, expr):
        # once(expr) => within(1, MAX, expr)
        return TemporalWithin(1, PyExpr("MAX"), expr)

    def next_call(self, expr):
        # next(expr) => within(1, 1, expr)
        return TemporalWithin(1, 1, expr)

    def implication(self, left, right):
        if isinstance(left, TemporalWithin):
            # Antecedent is temporal: use history-based evaluation
            left = TemporalHistory(
                left.min_occurrences,
                left.window,
                left.expr
            )
        return Implies(left, right)

    def forall(self, var, set_expr, body):
        return ForAll(str(var), set_expr, body)

    def NAME(self, token):
        return str(token)

    def NUMBER(self, token):
        return int(token)

    def MAX(self, token):
        return PyExpr("MAX")


# Singleton parser + transformer
_parser = ConstraintParser()
_transformer = ConstraintASTTransformer()

def parse_constraint(text: str):
    parsed = _parser.parse(text)
    return _transformer.transform(parsed)


if __name__ == "__main__":
    examples = [
        "once(`len(attack) >= 1`)",
        "forall field in `fields`: always(`len(protecting[field]) <= field.drones_for_full_protection`)",
        "scattered(3, `len(spawn_farmer) >= 2 or len(spawn_warrior) >= 2`)",
        "once(`len(cave) >= 1`) implies once(`len(attack) >= 1`)",
    ]
    for example in examples:
        print(f"Parsing: {example}")
        print(_parser.parse(example).pretty())
        ast = parse_constraint(example)
        print("AST:", ast)
        print()
