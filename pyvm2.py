"""A pure-Python Python bytecode interpreter."""
# Adapted from:
# 1. pyvm2 by Paul Swartz (z3p), from http://www.twistedmatrix.com/users/z3p/
# 2. byterun by Ned Batchelder, github.com/nedbat/byterun

import collections
import operator

import bytecode


class Frame(object):
    def __init__(self, code_obj, local_names, prev_frame):
        self.code_obj = code_obj
        self.local_names = local_names
        self.prev_frame = prev_frame
        self.stack = []
        self.last_instruction = 0
        self.block_stack = []

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


# class Function(object):
#     __slots__ = [
#         'func_code', 'func_name', 'func_defaults', 'func_globals',
#         'func_locals', 'func_dict', 'func_closure',
#         '__name__', '__dict__', '__doc__',
#         '_vm', '_func',
#     ]
#
#     def __init__(self, name, code, globs, defaults, closure, vm):
#         self._vm = vm
#         self.func_code = code
#         self.func_name = self.__name__ = name or code.co_name
#         self.func_defaults = tuple(defaults)
#         self.func_globals = globs
#         self.func_locals = self._vm.frame.local_names
#         self.__dict__ = {}
#         self.__doc__ = code.co_consts[0] if code.co_consts else None
#
#     def __call__(self, *args):
#         callargs = inspect.getcallargs(self._func, *args, **kwargs)
#         frame = self._vm.make_frame(
#             self.func_code, callargs, self.func_globals, {}
#         )
#         return self._vm.run_frame(frame)
#

class VirtualMachineError(Exception):
    pass


class VirtualMachine(object):
    def __init__(self):
        self.frames = []  # The call stack of frames.
        self.current_frame = None  # The current frame.
        self.return_value = None

    # Frame manipulation
    def make_frame(self, code, call_args=None, local_names=None):
        if call_args is None:
            call_args = {}
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

    # Jumping through bytecode
    def jump(self, jump):
        """Move the bytecode pointer to `jump`, so it will execute next."""
        self.current_frame.last_instruction = jump

    def run_code(self, code, local_names=None):
        """ An entry point to execute code using the virtual machine."""
        frame = self.make_frame(code, local_names=local_names)

        self.run_frame(frame)
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
        byte_name, arg_val = f.code_obj.co_code[op_offset]
        f.last_instruction += 1
        if arg_val:
            if byte_name in bytecode.HAVE_CONST:  # Look up a constant
                arg = f.code_obj.co_consts[arg_val]
            elif byte_name in bytecode.HAVE_NAME:  # Look up a name
                arg = f.code_obj.co_names[arg_val]
            else:
                arg = arg_val
            argument = [arg]
        else:
            argument = []

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

    # Stack manipulation

    def byte_LOAD_CONST(self, const):
        self.current_frame.push(const)

    def byte_POP_TOP(self):
        self.current_frame.pop()

    def byte_DUP_TOP(self):
        self.current_frame.push(self.current_frame.top())

    # Names
    def byte_LOAD_NAME(self, name):
        frame = self.current_frame
        if name in frame.local_names:
            val = frame.local_names[name]
        elif name in frame.global_names:
            val = frame.global_names[name]
        elif name in frame.builtin_names:
            val = frame.builtin_names[name]
        else:
            raise NameError("name '%s' is not defined" % name)
        self.current_frame.push(val)

    def byte_STORE_NAME(self, name):
        self.current_frame.local_names[name] = self.current_frame.pop()

    def byte_DELETE_NAME(self, name):
        del self.current_frame.local_names[name]

    def byte_LOAD_FAST(self, name):
        if name in self.current_frame.local_names:
            val = self.current_frame.local_names[name]
        else:
            raise UnboundLocalError(
                "local variable '%s' referenced before assignment" % name
            )
        self.current_frame.push(val)

    def byte_STORE_FAST(self, name):
        self.current_frame.local_names[name] = self.current_frame.pop()

    def byte_LOAD_GLOBAL(self, name):
        f = self.current_frame
        if name in f.global_names:
            val = f.global_names[name]
        elif name in f.builtin_names:
            val = f.builtin_names[name]
        else:
            raise NameError("global name '%s' is not defined" % name)
        f.push(val)

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
        self.current_frame.push(elements)

    def byte_BUILD_MAP(self, size):
        self.current_frame.push({})

    def byte_STORE_MAP(self):
        the_map, val, key = self.current_frame.popn(3)
        the_map[key] = val
        self.current_frame.push(the_map)

    def byte_UNPACK_SEQUENCE(self, count):
        seq = self.current_frame.pop()
        for x in reversed(seq):
            self.current_frame.push(x)

    def byte_BUILD_SLICE(self, count):
        if count == 2:
            x, y = self.current_frame.popn(2)
            self.current_frame.push(slice(x, y))
        elif count == 3:
            x, y, z = self.current_frame.popn(3)
            self.current_frame.push(slice(x, y, z))
        else:  # pragma: no cover
            raise VirtualMachineError("Strange BUILD_SLICE count: %r" % count)

    def byte_LIST_APPEND(self, count):
        val = self.current_frame.pop()
        the_list = self.current_frame.stack[-count]  # peek
        the_list.append(val)

    # Jumps

    def byte_JUMP_FORWARD(self, jump):
        self.jump(jump)

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

    def byte_JUMP_IF_TRUE_OR_POP(self, jump):
        val = self.current_frame.top()
        if val:
            self.jump(jump)
        else:
            self.current_frame.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, jump):
        val = self.current_frame.top()
        if not val:
            self.jump(jump)
        else:
            self.current_frame.pop()

    # Blocks

    def byte_SETUP_LOOP(self, dest):
        self.current_frame.push_block('loop', dest)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_CONTINUE_LOOP(self, destination):
        # This is a trick with the return value.
        # While unrolling blocks, continue and return both have to preserve
        # state as the finally blocks are executed.  For continue, it's
        # where to jump to, for return, it's the value to return.  It gets
        # pushed on the stack for both, so continue puts the jump destination
        # into return_value.
        self.return_value = destination
        return 'continue'

    def byte_POP_BLOCK(self):
        self.current_frame.pop_block()

    # Functions

    # def byte_MAKE_FUNCTION(self, argc):
    #     name = self.current_frame.pop()
    #     code = self.current_frame.pop()
    #     defaults = self.current_frame.popn(argc)
    #     globs = self.current_frame.global_names
    #     # TODO: if we're not supporting kwargs, do we need the defaults?
    #     fn = Function(name, code, globs, defaults, None, self)
    #     self.current_frame.push(fn)
    #
    # def byte_CALL_FUNCTION(self, arg):
    #     lenKw, lenPos = divmod(arg, 256)  # KWargs not supported in byterun
    #     posargs = self.current_frame.popn(lenPos)
    #
    #     func = self.current_frame.pop()
    #     frame = self.current_frame
    #     retval = func(*posargs)
    #     self.current_frame.push(retval)
    #
    # def byte_RETURN_VALUE(self):
    #     self.return_value = self.current_frame.pop()
    #     return "return"

