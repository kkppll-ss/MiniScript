class Value:
    def __init__(self, dtype: str, value):
        self.dtype = dtype
        self.value = value

    def __str__(self):
        return str((self.dtype, self.value))

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

    def __neg__(self):
        if self.dtype != 'int' and self.dtype != 'real':
            raise TypeError('to negative, the type of operand must be number')
        return Value(self.dtype, -self.value)

    def __bool__(self):
        if self.dtype != 'bool':
            raise TypeError('you should check bool with a bool value')
        return self.value


class CodeObj:
    def __init__(self, code, const_list, name_list):
        self.code = code
        self.const_list = const_list
        self.name_list = name_list

    def __str__(self):
        return """CodeObj object: begin
the const list is:
{}
the name list is:
{}
The code is:
{}
end""".format(self.const_list, self.name_list, self.code)

    def __repr__(self):
        return str(self)


class Function:
    def __init__(self, parameter_list: [str], code_obj: CodeObj, lexical_depth: int):
        self.parameter_list = parameter_list
        self.code_obj = code_obj
        self.lexical_depth = lexical_depth

    def __str__(self):
        return str((self.lexical_depth, self.parameter_list, self.code_obj))

    def __repr__(self):
        return str(self)


