import ply.lex as lex

reserved_word = {
    'for': 'FOR',
    'while': 'WHILE',
    'if': 'IF',
    'else': 'ELSE',
    'print': 'PRINT',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT'
}

tokens = [
             'INT',
             'REAL',
             'STRING',
             'ID',
             'PLUS',
             'MINUS',
             'TIMES',
             'DIVIDE',
             'UNARY_MINUS',
             'INCOMPLETE_IF',
             'ASSIGN',
             'EQUAL',
             'NOT_EQUAL',
             'GREATER',
             'LESS',
             'GREATER_EQUAL',
             'LESS_EQUAL',
             'LEFT_BRACE',
             'RIGHT_BRACE',
             'LEFT_PAREN',
             'RIGHT_PAREN',
             'SEMICOLON',
         ] + list(reserved_word.values())


def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_REAL(t):
    r'[0-9]*\.[0-9]+'
    t.value = float(t.value)
    return t


def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value[1:len(t.value)]
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved_word.get(t.value, 'ID')  # Check for reserved words
    return t


t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_LEFT_BRACE = r'\{'
t_RIGHT_BRACE = r'\}'
t_LEFT_PAREN = r'\('
t_RIGHT_PAREN = r'\)'
t_ASSIGN = r'='
t_SEMICOLON = r';'
t_EQUAL = r'=='
t_NOT_EQUAL = r'!='
t_GREATER = r'>'
t_LESS = r'<'
t_GREATER_EQUAL = r'>='
t_LESS_EQUAL = r'<='
t_ignore = ' \t'


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


lexer = lex.lex()
