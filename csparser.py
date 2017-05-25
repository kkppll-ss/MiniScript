import json
from collections import OrderedDict
from typing import Optional

import collections
import ply.yacc as yacc
import sys
from cslexer import tokens

precedence = (
    ('nonassoc', 'INCOMPLETE_IF'),
    ('nonassoc', 'ELSE'),
    ('left', 'AND', 'OR'),
    ('left', 'EQUAL', 'NOT_EQUAL'),
    ('left', 'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'NOT', 'UNARY_MINUS')
)


class Value:
    def __init__(self, dtype: str, value):
        self.dtype = dtype
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self)

    def _check_type(self, other):
        if self.dtype != other.dtype:
            raise TypeError('the compare of = for {} and {} is error, the first is of type {} '
                            'but the latter is of type {}'.format(self, other, self.dtype, other.dtype))

    def __eq__(self, other):
        return Value('bool', self.dtype == other.dtype and self.value == other.value)

    def __le__(self, other):
        self._check_type(other)
        return Value('bool', self.value < other.value)

    def __ge__(self, other):
        self._check_type(other)
        return Value('bool', self.value >= other.value)

    def __lt__(self, other):
        self._check_type(other)
        return Value('bool', self.value < other.value)

    def __gt__(self, other):
        self._check_type(other)
        return Value('bool', self.value > other.value)

    def __ne__(self, other):
        return Value('bool', not(self == other))

    def __add__(self, other):
        self._check_type(other)
        return Value(self.dtype, self.value + other.value)

    def __sub__(self, other):
        self._check_type(other)
        if self.dtype != 'int' and self.dtype != 'real':
            raise TypeError('to subtract, the type of operand must be number')
        return Value(self.dtype, self.value - other.value)

    def __mul__(self, other):
        self._check_type(other)
        if self.dtype != 'int' and self.dtype != 'real':
            raise TypeError('to multiply, the type of operand must be number')
        return Value(self.dtype, self.value * other.value)

    def __truediv__(self, other):
        self._check_type(other)
        if self.dtype != 'int' and self.dtype != 'real':
            raise TypeError('to divide, the type of operand must be number')
        return Value(self.dtype, self.value / other.value)

    def __bool__(self):
        if self.dtype != 'bool':
            raise TypeError('you should check bool with a bool value')
        return self.value


symbolTable = {}  # type: {str}
constTable = []  # type: [Value]
nameTable = []  # type: [str]


class Counter:
    def __init__(self, init_value):
        self.value = init_value


def label_counter(init_value=0):
    counter = Counter(init_value)

    def increment():
        old_label_count = counter.value
        counter.value += 1
        return old_label_count

    return increment


next_label = label_counter()


class StatNode:
    def __init__(self):
        self.type = None  # type: str
        self.children = None

    def perform_operation(self):
        raise NotImplementedError

    def emit_code(self) -> str:
        return NotImplemented


class ExpNode:
    def __init__(self):
        self.type = None  # type: str
        self.children = None  # type: OrderedDict

    def perform_operation(self):
        return NotImplemented

    def emit_code(self) -> str:
        return NotImplemented


class ConstExpNode(ExpNode):
    def __init__(self, index: int):
        super().__init__()
        self.type = 'const'
        self.children = {'index': index}

    def perform_operation(self):
        return constTable[self.children['index']].value

    def emit_code(self):
        return 'LOAD_CONST {}'.format(self.children['index'])


class IDExpNode(ExpNode):
    def __init__(self, index: int):
        super().__init__()
        self.type = 'id'
        self.children = {'index': index}

    def perform_operation(self):
        return symbolTable[nameTable[self.children['index']]]

    def emit_code(self):
        return 'LOAD_NAME {}'.format(self.children['index'])


class BinaryExpNode(ExpNode):
    def __init__(self, left: ExpNode, right: ExpNode, operator: str):
        super().__init__()
        self.type = 'binary'
        self.children = OrderedDict([('operator', operator), ('left', left), ('right', right)])

    def perform_operation(self):
        [operator, left, right] = self.children.values()
        if operator == '+':
            return left.perform_operation() + right.perform_operation()
        elif operator == '-':
            return left.perform_operation() - right.perform_operation()
        elif operator == '*':
            return left.perform_operation() * right.perform_operation()
        elif operator == '/':
            return left.perform_operation() / right.perform_operation()
        elif operator == 'and':
            return left.perform_operation() and right.perform_operation()
        elif operator == 'or':
            return left.perform_operation() or right.perform_operation()
        elif operator == '!=':
            return left.perform_operation() != right.perform_operation()
        elif operator == '==':
            return left.perform_operation() == right.perform_operation()
        elif operator == '>':
            return left.perform_operation() > right.perform_operation()
        elif operator == '<':
            return left.perform_operation() < right.perform_operation()
        elif operator == '>=':
            return left.perform_operation() >= right.perform_operation()
        elif operator == '<=':
            return left.perform_operation() <= right.perform_operation()

    def emit_code(self):
        [operator, left, right] = self.children.values()
        left_code = left.emit_code()
        right_code = right.emit_code()
        operator_code = 'UNKNOWN_BINARY_OPERATOR'
        if operator == '+':
            operator_code = 'BINARY_ADD'
        elif operator == '-':
            operator_code = 'BINARY_SUBTRACT'
        elif operator == '*':
            operator_code = 'BINARY_MULTIPLY'
        elif operator == '/':
            operator_code = 'BINARY_DIVIDE'
        elif operator == 'and':
            operator_code = 'BINARY_AND'
        elif operator == 'or':
            operator_code = 'BINARY_OR'
        elif operator == '!=':
            operator_code = 'BINARY_NOT_EQUAL'
        elif operator == '==':
            operator_code = 'BINARY_EQUAL'
        elif operator == '>':
            operator_code = 'BINARY_GRATER'
        elif operator == '<':
            operator_code = 'BINARY_LESS'
        elif operator == '>=':
            operator_code = 'BINARY_GRATER_EQUAL'
        elif operator == '<=':
            operator_code = 'BINARY_LESS_EQUAL'
        return left_code + '\n' + right_code + '\n' + operator_code


class CompareExpNode(ExpNode):
    def __init__(self, left: ExpNode, right: ExpNode, operator: str):
        super().__init__()
        self.type = 'compare'
        self.children = OrderedDict([('operator', operator), ('left', left), ('right', right)])

    def perform_operation(self):
        [operator, left, right] = self.children.values()
        if operator == '!=':
            return left.perform_operation() != right.perform_operation()
        elif operator == '==':
            return left.perform_operation() == right.perform_operation()
        elif operator == '>':
            return left.perform_operation() > right.perform_operation()
        elif operator == '<':
            return left.perform_operation() < right.perform_operation()
        elif operator == '>=':
            return left.perform_operation() >= right.perform_operation()
        elif operator == '<=':
            return left.perform_operation() <= right.perform_operation()

    def emit_code(self):
        [operator, left, right] = self.children.values()
        left_code = left.emit_code()
        right_code = right.emit_code()
        operator_code = 'UNKNOWN_COMPARE_OPERATOR'
        if operator == '<':
            operator_code = 'COMPARE_OP 0'
        elif operator == '<=':
            operator_code = 'COMPARE_OP 1'
        elif operator == '==':
            operator_code = 'COMPARE_OP 2'
        elif operator == '!=':
            operator_code = 'COMPARE_OP 3'
        elif operator == '>':
            operator_code = 'COMPARE_OP 4'
        elif operator == '>=':
            operator_code = 'COMPARE_OP 5'
        return left_code + '\n' + right_code + '\n' + operator_code


class UnaryExpNode(ExpNode):
    def __init__(self, exp: ExpNode, operator: str):
        super().__init__()
        self.type = 'unary'
        self.children = OrderedDict(([('operator', operator), ('exp', exp)]))

    def perform_operation(self):
        [operator, exp] = self.children.values()
        if operator == '-':
            return -exp.perform_operation()
        elif operator == 'not':
            return not exp.perform_operation()

    def emit_code(self):
        [operator, exp] = self.children.values()
        exp_code = exp.emit_code()
        operator_code = 'UNKNOWN_UNARY_OPERATOR'
        if operator == '-':
            operator_code = 'UNARY_NEGATIVE'
        elif operator == 'not':
            operator_code = 'UNARY_NOT'
        return exp_code + '\n' + operator_code


class StatListNode:
    def __init__(self, current_stat: StatNode):
        self.children = [current_stat]

    def prepend_stat(self, stat: StatNode):
        self.children.insert(0, stat)

    def perform_operation(self):
        for child in self.children:
            child.perform_operation()

    def emit_code(self):
        list_code_array = [stat.emit_code() for stat in self.children]
        list_code = '\n'.join(list_code_array)
        return list_code


class ProgramNode(StatNode):
    def __init__(self, stat_list: StatListNode):
        super().__init__()
        self.type = 'program'
        self.children = {'stat_list': stat_list}

    def perform_operation(self):
        self.children['stat_list'].perform_operation()

    def emit_code(self):
        item = Value('NoneType', None)
        if item not in constTable:
            constTable.append(item)
        index = constTable.index(item)
        stat_code = self.children['stat_list'].emit_code()
        return_code = """LOAD_CONST {}
RETURN_VALUE""".format(index)
        return stat_code + '\n' + return_code


class CompoundStatNode(StatNode):
    def __init__(self, stat_list: StatListNode):
        super().__init__()
        self.type = 'compound'
        self.children = {'stat_list': stat_list}

    def perform_operation(self):
        self.children['stat_list'].perform_operation()

    def emit_code(self):
        return self.children['stat_list'].emit_code()


class AssignStatNode(StatNode):
    def __init__(self, id_index: int, exp: ExpNode):
        super().__init__()
        self.type = 'assign'
        self.children = OrderedDict([('id_index', id_index), ('exp', exp)])

    def perform_operation(self):
        [id_index, exp] = self.children.values()
        symbolTable[nameTable[id_index]] = exp.perform_operation()

    def emit_code(self):
        [id_index, exp] = self.children.values()
        exp_code = exp.emit_code()
        assign_code = 'STORE_NAME {}'.format(id_index)
        return exp_code + '\n' + assign_code


class BreakStatNode(StatNode):
    def __init__(self):
        super().__init__()
        self.type = 'break'
        self.children = None

    def emit_code(self):
        return 'BREAK_LOOP'

    def perform_operation(self):
        raise NotImplementedError


class PrintStatNode(StatNode):
    def __init__(self, exp: ExpNode):
        super().__init__()
        self.type = 'print'
        self.children = {'exp': exp}

    def perform_operation(self):
        exp = self.children['exp']
        print(exp.perform_operation())

    def emit_code(self):
        exp_code = self.children['exp'].emit_code()
        print_code = 'PRINT_EXPR'
        return exp_code + '\n' + print_code


class WhileStatNode(StatNode):
    def __init__(self, condition_exp: BinaryExpNode, body_stat: StatNode):
        super().__init__()
        self.type = 'while'
        self.children = OrderedDict([('condition', condition_exp), ('body', body_stat)])

    def perform_operation(self):
        [condition, body] = self.children.values()
        while bool(condition.perform_operation()):
            body.perform_operation()

    def emit_code(self):
        [condition, body] = self.children.values()
        condition_code = condition.emit_code()
        body_code = body.emit_code()
        while_code = """SETUP_LOOP L{0}
L{1}:
{2}
POP_JUMP_IF_FALSE L{3}
{4}
JUMP_ABSOLUTE L{1}
L{3}:
POP_BLOCK
L{0}:""".format(next_label(), next_label(), condition_code, next_label(), body_code)
        return while_code


class ForStatNode(StatNode):
    def __init__(self, init_stat: AssignStatNode, condition_exp: BinaryExpNode,
                 loop_stat: AssignStatNode, body_stat: StatNode):
        super().__init__()
        self.type = 'for'
        self.children = OrderedDict([('init', init_stat), ('condition', condition_exp),
                                     ('loop', loop_stat), ('body', body_stat)])

    def perform_operation(self):
        [init, condition, loop, body] = self.children.values()
        init.perform_operation()
        while bool(condition.perform_operation()):
            body.perform_operation()
            loop.perform_operation()

    def emit_code(self):
        [init, condition, loop, body] = self.children.values()
        init_code = init.emit_code()
        condition_code = condition.emit_code()
        loop_code = loop.emit_code()
        for_code = """{0}
SETUP_LOOP L{1}
L{2}:
{3}
POP_JUMP_IF_FALSE L{4}
{5}
{6}
JUMP_ABSOLUTE L{2}
L{4}:
POP_BLOCK
L{1}:""".format(init_code, next_label(), next_label(), condition_code, next_label(),
                body.emit_code(), loop_code)
        return for_code


class BranchStatNode(StatNode):
    def __init__(self, if_exp: BinaryExpNode, if_stat: StatNode, else_stat: Optional[StatNode]):
        super().__init__()
        self.type = 'branch'
        self.children = OrderedDict([('if_exp', if_exp), ('if_stat', if_stat), ('else_stat', else_stat)])

    def perform_operation(self):
        [if_exp, if_stat, else_stat] = self.children.values()
        if bool(if_exp.perform_operation()):
            if_stat.perform_operation()
        elif else_stat:
            else_stat.perform_operation()

    def emit_code(self):
        [if_exp, if_stat, else_stat] = self.children.values()
        if_exp_code = if_exp.emit_code()
        if else_stat:
            branch_code = """{0}
POP_JUMP_IF_FALSE L{1}
{2}
JUMP_ABSOLUTE L{3}
L{1}:
{4}
L{3}:""".format(if_exp_code, next_label(), if_stat.emit_code(), next_label(),
                else_stat.emit_code())
        else:
            branch_code = """{0}
POP_JUMP_IF_FALSE L{1}
{2}
L{1}:""".format(if_exp_code, next_label(), if_stat.emit_code())
        return branch_code


class Function:
    def __init__(self, argument, statement):
        self.argument = argument
        self.statement = statement


class FunctionExpNode(ExpNode):
    def __init__(self, name, argument_list, stat):
        super().__init__()
        self.type = 'function'
        self.children = {'name': name, 'argument': argument_list, 'statement': stat}

        def export_to_environment(name, argument, statement):
            symbolTable[name] = Function(argument, statement)


class SyntaxTreeJSONEncoder(json.JSONEncoder):
    def default(self, tree_node: StatNode or ExpNode or StatListNode):
        if isinstance(tree_node, StatNode) or isinstance(tree_node, ExpNode):
            return OrderedDict([('type', tree_node.type), ('children', tree_node.children)])
        if isinstance(tree_node, StatListNode):
            return OrderedDict([('children', tree_node.children)])
        return json.JSONEncoder.default(self, tree_node)


def p_program(p):
    """
    program : statement_list
    """
    p[0] = ProgramNode(p[1])


def p_statement_list(p):
    """
    statement_list : statement 
                  | statement statement_list
    """
    if len(p) == 2:
        p[0] = StatListNode(p[1])
    else:
        p[0] = p[2]
        p[0].prepend_stat(p[1])


def p_statement(p):
    """
    statement : compound_statement
            |  branch_statement
            |  while_statement
            |  for_statement
            |  assign_statement
            |  print_statement
            |  break_statement
    """
    p[0] = p[1]


def p_compound_statement(p):
    """
    compound_statement : LEFT_BRACE statement_list RIGHT_BRACE
    """
    p[0] = CompoundStatNode(p[2])


def p_branch_statement(p):
    """
    branch_statement : IF LEFT_PAREN expression RIGHT_PAREN statement %prec INCOMPLETE_IF
                     | IF LEFT_PAREN expression RIGHT_PAREN statement ELSE statement
    """
    if len(p) == 6:
        p[0] = BranchStatNode(p[3], p[5], None)
    else:
        p[0] = BranchStatNode(p[3], p[5], p[7])


def p_while_statement(p):
    """
    while_statement : WHILE LEFT_PAREN expression RIGHT_PAREN statement
    """
    p[0] = WhileStatNode(p[3], p[5])


def p_for_statement(p):
    """
    for_statement : FOR LEFT_PAREN statement SEMICOLON expression SEMICOLON statement RIGHT_PAREN statement
    """
    p[0] = ForStatNode(p[3], p[5], p[7], p[9])


def p_assign_statement(p):
    """
    assign_statement : ID ASSIGN expression
    """
    if p[1] not in nameTable:
        nameTable.append(p[1])
    p[0] = AssignStatNode(nameTable.index(p[1]), p[3])


def p_break_statement(p):
    """
    break_statement : BREAK
    """
    p[0] = BreakStatNode()


def p_print_statement(p):
    """
    print_statement : PRINT expression
    """
    p[0] = PrintStatNode(p[2])


def p_binary_expression(p):
    """
    expression : expression PLUS expression
              | expression MINUS expression
              | expression TIMES expression
              | expression DIVIDE expression
              | expression AND expression
              | expression OR expression
    """
    p[0] = BinaryExpNode(p[1], p[3], p[2])


def p_compare_expression(p):
    """
    expression :   expression EQUAL expression
                 | expression NOT_EQUAL expression
                 | expression GREATER expression
                 | expression LESS expression
                 | expression GREATER_EQUAL expression
                 | expression LESS_EQUAL expression
    """
    p[0] = CompareExpNode(p[1], p[3], p[2])


def p_unary_expression(p):
    """
    expression : MINUS expression %prec UNARY_MINUS
              | NOT expression 
    """
    p[0] = UnaryExpNode(p[2], p[1])


def p_paren_expression(p):
    """
    expression : LEFT_PAREN expression RIGHT_PAREN
    """
    p[0] = p[2]


def p_expression_int(p):
    """
    expression : INT
    """
    exp_item = Value('int', p[1])
    if exp_item not in constTable:
        constTable.append(exp_item)
    p[0] = ConstExpNode(constTable.index(exp_item))


def p_expression_real(p):
    """
    expression : REAL
    """
    exp_item = Value('real', p[1])
    if exp_item not in constTable:
        constTable.append(exp_item)
    p[0] = ConstExpNode(constTable.index(exp_item))


def p_expression_string(p):
    """
    expression : STRING
    """
    exp_item = Value('str', p[1])
    if exp_item not in constTable:
        constTable.append(exp_item)
    p[0] = ConstExpNode(constTable.index(exp_item))


def p_expression_id(p):
    """
    expression : ID
    """
    index = nameTable.index(p[1])
    p[0] = IDExpNode(index)


def p_error(p):
    print("Syntax error in row {0} and column {1}, the input token is {2}".format(p.lineno, p.lexpos,
                                                                                  p.value))


def generate_code(program: str):
    parser = yacc.yacc()
    result = parser.parse(program)
    print("the JSON format is:")
    print(SyntaxTreeJSONEncoder(indent=4, separators=(',', ': ')).encode(result))
    code = result.emit_code()
    print("the code is")
    print(code)
    return{'co_code': code, 'co_consts': constTable, 'co_names': nameTable}

