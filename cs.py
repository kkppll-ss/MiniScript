import sys

import csparser
import vm
import labelconverter
import pickle
from value import CodeObj


def convert_label_recursive(code_obj: CodeObj):
    code_obj.code = labelconverter.convert(code_obj.code)
    for const_item in code_obj.const_list:
        if const_item.dtype == 'function':
            convert_label_recursive(const_item.value.code_obj)


def compile(file_name: str, output_name: str):
    with open(file_name, 'r') as program_file:
        program = program_file.read()
        code_obj = csparser.generate_code(program)
        convert_label_recursive(code_obj)
        print('the generated code is:\n{}'.format(code_obj))
        output = open(output_name, 'wb')
        pickle.dump(code_obj, output)


def run(file_name: str):
    virtual_machine = vm.VirtualMachine()
    with open(file_name, 'rb') as file:
        code = pickle.load(file)
        virtual_machine.run_code(code)


if __name__ == '__main__':
    if sys.argv[1] == 'compile':
        file_name, output_name = sys.argv[2:4]
        compile(file_name, output_name)
    elif sys.argv[1] == 'run':
        file_name = sys.argv[2]
        run(file_name)
    else:
        raise ValueError('command unrecognized!')
