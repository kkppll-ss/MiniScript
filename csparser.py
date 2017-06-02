import json
from collections import OrderedDict
from typing import Optional
import ply.yacc as yacc
import sys
import logging
from copy import deepcopy
from manager import ScopeManager
from bytecode import *
from cslexer import tokens
from value import Value, Function, CodeObj
import labelconverter
precedence = (
    ('nonassoc', 'INCOMPLETE_IF'),
    ('nonassoc', 'ELSE'),
    ('nonassoc', 'RETURN'),
    ('nonassoc', 'PRINT'),
    ('nonassoc', 'ASSIGN'),
    ('left', 'AND', 'OR'),
    ('left', 'EQUAL', 'NOT_EQUAL'),
    ('left', 'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'NOT', 'UNARY_MINUS'),
    ('left', 'LEFT_PAREN', 'LEFT_BRACKET', 'DOT'),
)


logging.basicConfig(
    level = logging.DEBUG,
    filename = "parselog.txt",
    filemode = "w",
    format = "%(filename)10s:%(lineno)4d:%(message)s"
)
log = logging.getLogger()


class ParameterList:
    def __init__(self, init_item=None):
        if not init_item:
            self.parameters = []
        else:
            self.parameters = [init_item]

    def prepend_item(self, item):
        self.parameters.insert(0, item)

    def get_parameters(self):
        return self.parameters

current_parameter_list = ParameterList()
scope_manager = ScopeManager()


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

    def emit_code(self) -> str:
        return NotImplemented


class ExpNode:
    def __init__(self):
        self.type = None  # type: str
        self.children = None  # type: OrderedDict

    def emit_code(self) -> str:
        return NotImplemented


class ListNode:
    def __init__(self, init_item=None):
        self.type = None  # type: str
        if not init_item:
            self.children = []
        else:
            self.children = [init_item]

    def emit_code(self):
        code_array = [item.emit_code() for item in self.children]
        code = '\n'.join(code_array)
        return code

    def prepend_item(self, item):
        self.children.insert(0, item)


class ConstExpNode(ExpNode):
    def __init__(self, index: int):
        super().__init__()
        self.type = 'const'
        self.children = {'index': index}

    def emit_code(self):
        return 'LOAD_CONST {}'.format(self.children['index'])


class IDExpNode(ExpNode):
    def __init__(self, index: int):
        super().__init__()
        self.type = 'id'
        self.children = {'index': index}

    def emit_code(self):
        return 'LOAD_NAME {}'.format(self.children['index'])


class BinaryExpNode(ExpNode):
    def __init__(self, left: ExpNode, right: ExpNode, operator: str):
        super().__init__()
        self.type = 'binary'
        self.children = OrderedDict([('operator', operator), ('left', left), ('right', right)])

    def emit_code(self):
        [operator, left, right] = self.children.values()
        left_code = left.emit_code()
        right_code = right.emit_code()
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
        elif operator == '[]':
            operator_code = 'BINARY_SUBSCR'
        else:
            raise ValueError('unrecognized binary operator {}'.format(operator))
        return left_code + '\n' + right_code + '\n' + operator_code


class CompareExpNode(ExpNode):
    def __init__(self, left: ExpNode, right: ExpNode, operator: str):
        super().__init__()
        self.type = 'compare'
        self.children = OrderedDict([('operator', operator), ('left', left), ('right', right)])

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
        self.children = OrderedDict([('operator', operator), ('exp', exp)])

    def emit_code(self):
        [operator, exp] = self.children.values()
        exp_code = exp.emit_code()
        operator_code = 'UNKNOWN_UNARY_OPERATOR'
        if operator == '-':
            operator_code = 'UNARY_NEGATIVE'
        elif operator == 'not':
            operator_code = 'UNARY_NOT'
        return exp_code + '\n' + operator_code


class ExpListNode(ListNode):
    def __init__(self, init_item=None):
        super().__init__(init_item)
        self.type = 'expression_list'


class MapElementExpNode(ExpNode):
    def __init__(self, key_expression: ExpNode, value_expression: ExpNode):
        super().__init__()
        self.type = 'map_element_expression'
        self.children = OrderedDict([('key_expression', key_expression), ('value_expression', value_expression)])

    def emit_code(self):
        key_expression, value_expression = self.children.values()
        key_exp_code = key_expression.emit_code()
        value_exp_code = value_expression.emit_code()
        return key_exp_code + '\n' + value_exp_code


class MapElementListNode(ListNode):
    def __init__(self, init_item=None):
        super().__init__(init_item)
        self.type = 'map_element_list'


class CallExpNode(ExpNode):
    def __init__(self, func_expression: ExpNode, expression_list: ExpListNode):
        super().__init__()
        self.type = 'call'
        self.children = OrderedDict([('func_expression', func_expression),
                                     ('expression_list', expression_list)])

    def emit_code(self):
        func_expression, expression_list = self.children.values()
        exp_code = expression_list.emit_code()
        load_function_code = func_expression.emit_code()
        call_function_code = 'CALL_FUNCTION'
        if exp_code:
            ret_code = exp_code + '\n' + load_function_code + '\n' + call_function_code
        else:
            ret_code = load_function_code + '\n' + call_function_code
        return ret_code


class ArrayExpNode(ExpNode):
    def __init__(self, expression_list: ExpListNode):
        super().__init__()
        self.type = 'array'
        self.children = {'expression_list': expression_list}

    def emit_code(self):
        expression_list = self.children['expression_list']
        exp_code = expression_list.emit_code()
        build_array_code = 'BUILD_LIST {}'.format(len(expression_list.children))
        if exp_code:
            ret_code = exp_code + '\n' + build_array_code
        else:
            ret_code = build_array_code
        return ret_code


class MapExpNode(ExpNode):
    def __init__(self, map_element_list: MapElementListNode):
        super().__init__()
        self.type = 'map'
        self.children = {'map_element_list': map_element_list}

    def emit_code(self):
        map_element_list = self.children['map_element_list']
        exp_code = map_element_list.emit_code()
        build_array_code = 'BUILD_MAP {}'.format(len(map_element_list.children))
        if exp_code:
            ret_code = exp_code + '\n' + build_array_code
        else:
            ret_code = build_array_code
        return ret_code


class StatListNode(ListNode):
    def __init__(self, init_item=None):
        super().__init__(init_item)
        self.type = 'statement-list'


class ProgramNode(StatNode):
    def __init__(self, stat_list: StatListNode):
        super().__init__()
        self.type = 'program'
        self.children = {'stat_list': stat_list}

    def emit_code(self):
        stat_code = self.children['stat_list'].emit_code()
        return stat_code


class CompoundStatNode(StatNode):
    def __init__(self, stat_list: StatListNode):
        super().__init__()
        self.type = 'compound'
        self.children = {'stat_list': stat_list}

    def emit_code(self):
        return self.children['stat_list'].emit_code()


class AssignStatNode(StatNode):
    def __init__(self, id_index: int, exp: ExpNode):
        super().__init__()
        self.type = 'assign'
        self.children = OrderedDict([('id_index', id_index), ('exp', exp)])

    def emit_code(self):
        [id_index, exp] = self.children.values()
        exp_code = exp.emit_code()
        assign_code = 'STORE_NAME {}'.format(id_index)
        return exp_code + '\n' + assign_code


class AssignSubscrStatNode(StatNode):
    def __init__(self, array_expression: ExpNode, subscr_expression: ExpNode, value_expression: ExpNode):
        super().__init__()
        self.type = 'assign_subscr_statement'
        self.children = OrderedDict([('array_expression', array_expression),
                                     ('subscr_expression', subscr_expression),
                                     ('value_expression', value_expression)])

    def emit_code(self):
        array_expression, subscr_expression, value_expression = self.children.values()
        array_exp_code = array_expression.emit_code()
        subscr_exp_code = subscr_expression.emit_code()
        value_exp_code = value_expression.emit_code()
        store_code = 'STORE_SUBSCR'
        return value_exp_code + '\n' + array_exp_code + '\n' + subscr_exp_code + '\n' + store_code


class BreakStatNode(StatNode):
    def __init__(self):
        super().__init__()
        self.type = 'break'
        self.children = None

    def emit_code(self):
        return 'BREAK_LOOP'


class PrintStatNode(StatNode):
    def __init__(self, exp: ExpNode):
        super().__init__()
        self.type = 'print'
        self.children = {'exp': exp}

    def emit_code(self):
        exp_code = self.children['exp'].emit_code()
        print_code = 'PRINT_EXPR'
        return exp_code + '\n' + print_code


class WhileStatNode(StatNode):
    def __init__(self, condition_exp: BinaryExpNode, body_stat: StatNode):
        super().__init__()
        self.type = 'while'
        self.children = OrderedDict([('condition', condition_exp), ('body', body_stat)])

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


class ExpStatNode(StatNode):
    def __init__(self, exp: ExpNode):
        super().__init__()
        self.type = 'exp_statement'
        self.children = {'expression': exp}

    def emit_code(self):
        expression = self.children['expression']
        exp_code = expression.emit_code()
        discard_code = 'POP_TOP'
        return exp_code + '\n' + discard_code


class ReturnStatNode(StatNode):
    def __init__(self, exp: ExpNode):
        super().__init__()
        self.type = 'return'
        self.children = {'exp': exp}

    def emit_code(self):
        exp_code = self.children['exp'].emit_code()
        return_code = 'RETURN_VALUE'
        return exp_code + '\n' + return_code


class SyntaxTreeJSONEncoder(json.JSONEncoder):
    def default(self, tree_node: StatNode or ExpNode or StatListNode):
        if isinstance(tree_node, StatNode) or isinstance(tree_node, ExpNode)\
                or isinstance(tree_node, ListNode):
            return OrderedDict([('type', tree_node.type), ('children', tree_node.children)])
        return json.JSONEncoder.default(self, tree_node)


def p_program(p):
    """
    program : statement_list
    """
    p[0] = ProgramNode(p[1])


def p_statement_list(p):
    """
    statement_list : statement statement_list
                    |
    """
    if len(p) == 1:
        p[0] = StatListNode()
    else:
        p[0] = p[2]
        p[0].prepend_item(p[1])


def p_statement(p):
    """
    statement : compound_statement
            |  branch_statement
            |  while_statement
            |  for_statement
            |  assign_statement
            |  assign_subscr_statement
            |  print_statement
            |  expression_statement
            |  break_statement
            |  return_statement
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
    assign_statement : ID ASSIGN seen_ASSIGN expression
    """
    t = scope_manager.find_name(p[1])
    p[0] = AssignStatNode(tuple2index(t), p[4])


def p_seen_ASSIGN(p):
    """
    seen_ASSIGN :
    """
    if not scope_manager.contains_name(p[-2]):
        scope_manager.append_name(p[-2])


def p_assign_subscr_statement(p):
    """
    assign_subscr_statement : expression LEFT_BRACKET expression RIGHT_BRACKET ASSIGN expression
    """
    p[0] = AssignSubscrStatNode(p[1], p[3], p[6])


def p_assign_dot_statement(p):
    """
    assign_subscr_statement : expression DOT ID ASSIGN expression
    """
    exp_item = Value('str', p[3])
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    subscr_node = ConstExpNode(scope_manager.find_const(exp_item))
    p[0] = AssignSubscrStatNode(p[1], subscr_node, p[5])


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


def p_expression_statement(p):
    """
    expression_statement : expression 
    """
    p[0] = ExpStatNode(p[1])


def p_return_statement(p):
    """
    return_statement : RETURN expression
    """
    p[0] = ReturnStatNode(p[2])


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


def p_binary_subscr_expression(p):
    """
    expression : expression LEFT_BRACKET expression RIGHT_BRACKET
    """
    p[0] = BinaryExpNode(p[1], p[3], '[]')


def p_binary_dot_expression(p):
    """
    expression : expression DOT ID
    """
    exp_item = Value('str', p[3])
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    subscr_node = ConstExpNode(scope_manager.find_const(exp_item))
    p[0] = BinaryExpNode(p[1], subscr_node, '[]')


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
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    p[0] = ConstExpNode(scope_manager.find_const(exp_item))


def p_expression_real(p):
    """
    expression : REAL
    """
    exp_item = Value('real', p[1])
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    p[0] = ConstExpNode(scope_manager.find_const(exp_item))


def p_expression_string(p):
    """
    expression : STRING
    """
    exp_item = Value('str', p[1])
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    p[0] = ConstExpNode(scope_manager.find_const(exp_item))


def p_expression_function(p):
    """
    expression : FUNCTION LEFT_PAREN parameter_list RIGHT_PAREN seen_FUNCTION LEFT_BRACE statement_list RIGHT_BRACE
    """
    parameter_list = p[3].get_parameters()
    statement_list = p[7]
    code = statement_list.emit_code()
    function_obj = CodeObj(code, scope_manager.current_const_list, scope_manager.current_name_list)
    exp_item = Value('function', Function(parameter_list, function_obj, scope_manager.current_lexical_depth))
    scope_manager.exit_scope()
    if not scope_manager.contains_const(exp_item):
        scope_manager.append_const(exp_item)
    index = scope_manager.find_const(exp_item)
    p[0] = ConstExpNode(index)


def p_seen_function(p):
    """
    seen_FUNCTION :
    """
    global current_parameter_list
    scope_manager.new_scope(current_parameter_list.get_parameters())
    current_parameter_list = ParameterList()


def p_expression_id(p):
    """
    expression : ID
    """
    t = scope_manager.find_name(p[1])
    p[0] = IDExpNode(tuple2index(t))


def p_call_expression(p):
    """
    expression : expression LEFT_PAREN expression_list RIGHT_PAREN
    """
    p[0] = CallExpNode(p[1], p[3])


def p_array_expression(p):
    """
    expression : LEFT_BRACKET expression_list RIGHT_BRACKET
    """
    p[0] = ArrayExpNode(p[2])


def p_expression_list(p):
    """
    expression_list :  expression COMMA expression_list
                    |  expression
                    |
    """
    if len(p) == 1:
        p[0] = ExpListNode()
    elif len(p) == 2:
        p[0] = ExpListNode(p[1])
    else:
        p[0] = p[3]
        p[0].prepend_item(p[1])


def p_map_element(p):
    """
    map_element_expression : expression COLON expression
    """
    p[0] = MapElementExpNode(p[1], p[3])


def p_map_element_list(p):
    """
    map_element_list :  map_element_expression
                      | map_element_expression COMMA map_element_list
                      |
    """
    if len(p) == 1:
        p[0] = MapElementListNode()
    elif len(p) == 2:
        p[0] = MapElementListNode(p[1])
    else:
        p[0] = p[3]
        p[0].prepend_item(p[1])


def p_map_expression(p):
    """
    expression : LEFT_BRACE map_element_list RIGHT_BRACE
    """
    p[0] = MapExpNode(p[2])


def p_parameter_list(p):
    """
    parameter_list :  ID COMMA parameter_list
                   | ID
                   |
    """
    global current_parameter_list
    if len(p) == 1:
        p[0] = ParameterList()
        current_parameter_list = deepcopy(p[0])
    elif len(p) == 2:
        p[0] = ParameterList(p[1])
        current_parameter_list = deepcopy(p[0])
    else:
        p[0] = p[3]
        p[0].prepend_item(p[1])
        current_parameter_list = deepcopy(p[0])


def p_error(p):
    print("Syntax error in row {0} and column {1}, the input token is {2}".format(p.lineno, p.lexpos,
                                                                                  p.value))


def generate_code(program: str):
    parser = yacc.yacc()
    result = parser.parse(program, debug=log)
    print("the JSON format is:")
    print(SyntaxTreeJSONEncoder(indent=4, separators=(',', ': ')).encode(result))
    code = result.emit_code()
    return CodeObj(code, scope_manager.current_const_list, scope_manager.current_name_list)


def main():
    program_filename = 'test.js'
    with open(program_filename, 'r') as program_file:
        program = program_file.read()
        code = generate_code(program)
        print(code)

if __name__ == '__main__':
    main()
