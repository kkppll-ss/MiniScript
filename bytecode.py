HAVE_CONST = ['LOAD_CONST']
HAVE_NAME = ['LOAD_NAME',
             'STORE_NAME']
HAVE_LABEL = ['JUMP_ABSOLUTE',
              'POP_JUMP_IF_TRUE',
              'POP_JUMP_IF_FALSE',
              'SETUP_LOOP']
HAVE_OTHER = ['COMPARE_OP', 'BUILD_LIST', 'BUILD_MAP']
HAVE_ARGUMENT = HAVE_LABEL + HAVE_NAME + HAVE_CONST + HAVE_OTHER


def tuple2index(t):
    lexical_depth, index = t
    return (lexical_depth << 8) + index


def index2tuple(storage_index):
    lexical_depth, index = divmod(storage_index, 256)
    return lexical_depth, index
