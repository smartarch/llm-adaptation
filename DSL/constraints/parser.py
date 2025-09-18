import os
from lark import Lark, Transformer, v_args

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


# === AST Node Classes ===
class ASTNode:
    pass

class PyExpr(ASTNode):
    def __init__(self, code):
        self.code = code
    def __repr__(self):
        return f"PyExpr({self.code!r})"

class TemporalWithin(ASTNode):
    def __init__(self, min_occurrences, window, expr):
        self.min_occurrences = min_occurrences  # PyExpr or number (as string)
        self.window = window  # PyExpr or number (as string)
        self.expr = expr  # ASTNode (usually PyExpr or BooleanOp)
    def __repr__(self):
        return f"Within(min_occurrences={self.min_occurrences!r}, window={self.window!r}, expr={self.expr!r})"

class BooleanOp(ASTNode):
    def __init__(self, op, *args):
        self.op = op  # 'and', 'or', 'not', 'implies'
        self.args = args
    def __repr__(self):
        return f"BooleanOp({self.op!r}, {', '.join(repr(a) for a in self.args)})"

class ForAll(ASTNode):
    def __init__(self, var, set_expr, body):
        self.var = var
        self.set_expr = set_expr  # PyExpr
        self.body = body  # ASTNode
    def __repr__(self):
        return f"ForAll({self.var!r}, {self.set_expr!r}, {self.body!r})"

# === AST Transformer ===
@v_args(inline=True)
class ConstraintASTTransformer(Transformer):
    def start(self, child):
        # Unwrap the top-level 'start' rule for a cleaner AST
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

    def and_(self, left, right):
        return BooleanOp('and', left, right)

    def or_(self, left, right):
        return BooleanOp('or', left, right)

    def not_(self, arg):
        return BooleanOp('not', arg)

    def implies(self, left, right):
        return BooleanOp('implies', left, right)

    def forall(self, var, set_expr, body):
        return ForAll(str(var), set_expr, body)

    def exists(self, *args):
        raise NotImplementedError("'exists' quantifier is not supported as per the spec.")

    def NAME(self, token):
        return str(token)

    def NUMBER(self, token):
        return int(token)

    def MAX(self, token):
        return PyExpr("MAX")


# Singleton instance for convenience
_parser = ConstraintParser()
_transformer = ConstraintASTTransformer()

def parse_constraint(text):
    parsed = _parser.parse(text)
    return _transformer.transform(parsed)


if __name__ == "__main__":
    examples = [
        "once(`len(attack) >= 1`)",
        "forall field in `fields`: always(`len(protecting[field]) <= field.drones_for_full_protection`)",
        "scattered(3, `len(spawn_farmer) >= 2 or len(spawn_warrior) >= 2`)",
    ]
    for example in examples:
        print(f"Parsing: {example}")
        print(_parser.parse(example).pretty())
        ast = parse_constraint(example)
        print("AST:", ast)
        print()
