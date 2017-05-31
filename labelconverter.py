import re
import bytecode


def unpack_instructions(program: str):
    program_array = program.split('\n')
    instructions = []
    for program_field in program_array:
        instruction, *arg = program_field.split()
        arg = arg[0] if arg else None
        instructions.append((instruction, arg))
    return instructions


def substitute_labels(instructions):
    labels = {}  # type: {str:int}
    inst_count = 0
    unmatched_labels = []
    pattern = re.compile(r'(L\d+):')
    for inst in instructions:
        match = pattern.fullmatch(inst[0])
        if match:
            unmatched_labels.append(match.group(1))
        else:
            if unmatched_labels:
                labels_to_update = {label: inst_count for label in unmatched_labels}
                labels.update(labels_to_update)
                unmatched_labels = []
            inst_count += 1
    ret_instructions = []
    for inst in instructions:
        if inst[0] in bytecode.HAVE_LABEL:
            ret_instructions.append((inst[0], labels[inst[1]]))
        elif inst[0] in bytecode.HAVE_ARGUMENT:
            ret_instructions.append((inst[0], int(inst[1])))
        elif not pattern.fullmatch(inst[0]):
            ret_instructions.append((inst[0], None))
    return ret_instructions


def convert(program: str):
    return substitute_labels(unpack_instructions(program))





