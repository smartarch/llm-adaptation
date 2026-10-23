import os
from lark import Lark, Transformer, v_args

from fcl.ast import Always, FCLError, ForAll, Implies, Node, Pred, Within


_GRAMMAR_PATH = os.path.join(os.path.dirname(__file__), 'grammar.lark')


@v_args(inline=True)
class _ASTTransformer(Transformer):
    """Transforms the Lark parse tree into the FCL AST."""

    def start(self, child):
        return child

    def py_expr(self, token):
        # Strip backticks, unescape \`
        code = str(token)[1:-1].replace('\\`', '`')
        return Pred(code)

    def number(self, token):
        return int(token)

    def max_const(self, _token):
        return "MAX"

    def beg_const(self, _token):
        return "BEG"

    def within(self, n, t, pred):
        return Within(n, t, pred)

    def always(self, body):
        _check_no_always(body, "always(...) cannot be nested in another always(...)")
        return Always(body)

    def implication(self, left, right):
        if isinstance(left, Within) and isinstance(left.t, int) and left.t > 0:
            raise FCLError(f"Antecedent of an implication must be a predicate or a past within (t < 0): {left}")
        if isinstance(right, Within) and isinstance(right.t, int) and right.t < 0:
            raise FCLError(f"Consequent of an implication must be a predicate or a future within (t > 0): {right}")
        return Implies(left, right)

    def forall(self, var, set_expr, body):
        return ForAll(str(var), set_expr, body)


def _check_no_always(node: Node, message: str):
    if isinstance(node, Always):
        raise FCLError(message)
    if isinstance(node, ForAll):
        _check_no_always(node.body, message)


def _create_parser() -> Lark:
    with open(_GRAMMAR_PATH, encoding='utf-8') as f:
        grammar = f.read()
    return Lark(grammar, parser='lalr', start='start', transformer=_ASTTransformer())


_parser = _create_parser()


def parse(text: str) -> Node:
    """Parse an FCL formula (in the DSL syntax) into an AST (`Formula`).

    Raises `lark.exceptions.LarkError` for syntax errors and `fcl.FCLError` for formulas outside the implemented subset.
    """
    try:
        return _parser.parse(text)
    except Exception as e:
        # errors raised in the transformer are wrapped by lark
        if isinstance(getattr(e, "orig_exc", None), FCLError):
            raise e.orig_exc from None
        raise
