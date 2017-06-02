"""A pure-Python Python bytecode interpreter."""
# Adapted from:
# 1. pyvm2 by Paul Swartz (z3p), from http://www.twistedmatrix.com/users/z3p/
# 2. byterun by Ned Batchelder, github.com/nedbat/byterun

import collections
import operator

import bytecode
from bytecode import index2tuple
from value import *


class Frame(object):
    def __init__(self, code_obj: CodeObj, local_names: {str: Value}, prev_frame):
        self.code_obj = code_obj  # type: CodeObj
        self.local_names = local_names  # type: {str: Value}
        self.prev_frame = prev_frame
        self.stack = []  # type: [Value]
        self.last_instruction = 0
        self.block_stack = []  # type: [Block]

    # Data stack manipulation
    def top(self):
        return self.stack[-1]

    def pop(self):
        return self.stack.pop()

    def push(self, *vals):
        self.stack.extend(vals)

    def popn(self, n):
        """Pop a number of values from the value stack.
        A list of `n` values is returned, the deepest value first.
        """
        if n:
            ret = self.stack[-n:]
            self.stack[-n:] = []
            return ret
        else:
            return []

    # Block stack manipulation
    def push_block(self, b_type, handler=None):
        stack_height = len(self.stack)
        self.block_stack.append(Block(b_type, handler, stack_height))

    def pop_block(self):
        return self.block_stack.pop()

    def unwind_block(self, block):
        """Unwind the values on the data stack when a given block is finished."""
        while len(self.stack) > block.stack_height:
            self.pop()


Block = collections.namedtuple("Block", "type, handler, stack_height")


class VirtualMachineError(Exception):
    pass


class VirtualMachine(object):
    def __init__(self):
        self.frames = []  # The call stack of frames.
        self.current_frame = None  # The current frame.
        self.return_value = None
        self.display_stack = {}  # type: {[int: Frame]}
        self.current_lexical_depth = None
        self.lexical_depth_stack = []
        self.display = {}

    # Frame manipulation
    def make_frame(self, code, call_args=None, local_names=None):
        if call_args is None:
            call_args = {}
        if local_names is None:
            local_names = {}
        local_names.update(call_args)
        frame = Frame(code, local_names, self.current_frame)
        return frame

    def push_frame(self, frame):
        self.frames.append(frame)
        self.current_frame = frame

    def pop_frame(self):
        self.frames.pop()
        if self.frames:
            self.current_frame = self.frames[-1]
        else:
            self.current_frame = None

    def push_display(self, lexical_depth, frame):
        if lexical_depth in self.display_stack:
            self.display_stack[lexical_depth].append(frame)
        else:
            self.display_stack[lexical_depth] = [frame]
        self.display[lexical_depth] = frame
        self.lexical_depth_stack.append(lexical_depth)
        self.current_lexical_depth = lexical_depth

    def pop_display(self):
        lexical_depth = self.current_lexical_depth
        self.display_stack[lexical_depth].pop()
        if self.display_stack[lexical_depth]:
            self.display[lexical_depth] = self.display_stack[lexical_depth][-1]
        else:
            self.display[lexical_depth] = None
        self.lexical_depth_stack.pop()
        if self.lexical_depth_stack:
            self.current_lexical_depth = self.lexical_depth_stack[-1]
        else:
            self.current_lexical_depth = None

    # Jumping through bytecode
    def jump(self, jump):
        """Move the bytecode pointer to `jump`, so it will execute next."""
        self.current_frame.last_instruction = jump

    def run_code(self, code, local_names=None):
        """ An entry point to execute code using the virtual machine."""
        frame = self.make_frame(code, local_names=local_names)
        self.push_display(0, frame)
        self.run_frame(frame)
        self.pop_display()
        # Check some invariants
        # if self.frames:
        #     raise VirtualMachineError("Frames left over!")
        # if self.frame and self.frame.stack:
        #     raise VirtualMachineError("Data left on stack! %r" % self.frame.stack)

        # for testing, was val = self.run_frame(frame)
        # return val # for testing

    def parse_byte_and_args(self):
        f = self.current_frame
        op_offset = f.last_instruction
        byte_name, arg_val = f.code_obj.code[op_offset]
        f.last_instruction += 1
        if arg_val is not None:
            if byte_name in bytecode.HAVE_CONST:  # Look up a constant
                arg = f.code_obj.const_list[arg_val]
            elif byte_name in bytecode.HAVE_NAME:  # Look up a name
                arg = index2tuple(arg_val)
            else:
                arg = arg_val
            argument = [arg]
        else:
            argument = []
        # print("the instruction: {} {}".format(byte_name, argument))
        return byte_name, argument

    def dispatch(self, byte_name, argument):
        """ Dispatch by bytename to the corresponding methods.
        Exceptions are caught and set on the virtual machine."""

        # When later unwinding the block stack,
        # we need to keep track of why we are doing it.
        why = None
        bytecode_fn = getattr(self, 'byte_%s' % byte_name, None)
        if bytecode_fn is None:
            if byte_name.startswith('UNARY_'):
                self.unaryOperator(byte_name[6:])
            elif byte_name.startswith('BINARY_'):
                self.binaryOperator(byte_name[7:])
            else:
                raise VirtualMachineError(
                    "unsupported bytecode type: %s" % byte_name
                )
        else:
            why = bytecode_fn(*argument)
        return why

    def manage_block_stack(self, why):
        block = self.current_frame.block_stack[-1]

        if block.type == 'loop' and why == 'continue':
            self.jump(self.return_value)
        elif block.type == 'loop' and why == 'break':
            self.current_frame.pop_block()
            self.current_frame.unwind_block(block)
            self.jump(block.handler)
        else:
            raise RuntimeError('the block type is {} and why is{}'.format(block.type, why))

    def run_frame(self, frame):
        """Run a frame until it returns (somehow).
        Exceptions are raised, the return value is returned.
        """
        self.push_frame(frame)
        while True:
            byte_name, argument = self.parse_byte_and_args()

            why = self.dispatch(byte_name, argument)

            # Deal with any block management we need to do
            if why:
                if frame.block_stack:
                    self.manage_block_stack(why)
                else:
                    break
        self.pop_frame()
        return self.return_value

    def call_function(self, func: Function, arguments: []):
        call_args = dict(zip(func.parameter_list, arguments))
        lexical_depth = func.lexical_depth
        frame = self.make_frame(func.code_obj, call_args)
        self.push_display(lexical_depth, frame)
        ret_value = self.run_frame(frame)
        self.pop_display()
        return ret_value

    def byte_LOAD_CONST(self, const):
        self.current_frame.push(const)

    def byte_POP_TOP(self):
        self.current_frame.pop()

    # Names
    def byte_LOAD_NAME(self, tuple_index):
        lexical_depth, index = tuple_index
        frame = self.display[lexical_depth]
        name = frame.code_obj.name_list[index]
        val = frame.local_names[name]
        self.current_frame.push(val)

    def byte_STORE_NAME(self, tuple_index):
        lexical_depth, index = tuple_index
        frame = self.display[lexical_depth]
        name = frame.code_obj.name_list[index]
        frame.local_names[name] = self.current_frame.pop()

    def byte_STORE_SUBSCR(self):
        val, obj, subscr = self.current_frame.popn(3)
        obj[subscr] = val

    # Operators

    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT': operator.not_,
        'INVERT': operator.invert,
    }

    def unaryOperator(self, op):
        x = self.current_frame.pop()
        self.current_frame.push(self.UNARY_OPERATORS[op](x))

    BINARY_OPERATORS = {
        'POWER': pow,
        'MULTIPLY': operator.mul,
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE': operator.truediv,
        'MODULO': operator.mod,
        'ADD': operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR': operator.getitem,
        'LSHIFT': operator.lshift,
        'RSHIFT': operator.rshift,
        'AND': operator.and_,
        'XOR': operator.xor,
        'OR': operator.or_,
    }

    def binaryOperator(self, op):
        x, y = self.current_frame.popn(2)
        self.current_frame.push(self.BINARY_OPERATORS[op](x, y))

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def byte_COMPARE_OP(self, op_num):
        x, y = self.current_frame.popn(2)
        self.current_frame.push(self.COMPARE_OPERATORS[op_num](x, y))

    # Building

    def byte_BUILD_TUPLE(self, count):
        elements = self.current_frame.popn(count)
        self.current_frame.push(tuple(elements))

    def byte_BUILD_LIST(self, count):
        elements = self.current_frame.popn(count)
        table = dict(enumerate(elements))
        self.current_frame.push(Value('table', table))

    def byte_BUILD_MAP(self, count):
        elements = self.current_frame.popn(2 * count)
        table = {elements[i]: elements[i+1] for i in range(0, len(elements), 2)}
        self.current_frame.push(Value('table', table))

    def byte_LIST_APPEND(self, count):
        val = self.current_frame.pop()
        the_list = self.current_frame.stack[-count]  # peek
        the_list.append(val)

    # Jumps

    def byte_JUMP_ABSOLUTE(self, jump):
        self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self, jump):
        val = self.current_frame.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):
        val = self.current_frame.pop()
        if not val:
            self.jump(jump)

    # Blocks

    def byte_SETUP_LOOP(self, destination):
        self.current_frame.push_block('loop', destination)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_POP_BLOCK(self):
        self.current_frame.pop_block()

    def byte_CALL_FUNCTION(self):
        func_value = self.current_frame.pop()
        func = func_value.value
        parameter_len = len(func.parameter_list)
        arguments = self.current_frame.popn(parameter_len)
        ret_value = self.call_function(func, arguments)
        self.current_frame.push(ret_value)

    def byte_RETURN_VALUE(self):
        self.return_value = self.current_frame.pop()
        return "return"

    # print
    def byte_PRINT_EXPR(self):
        value = self.current_frame.pop()
        print(value)
