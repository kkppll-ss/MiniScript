import sys

import msparser
import vm
import labelconverter
from value import CodeObj


def convert_label_recursive(code_obj: CodeObj):
    code_obj.code = labelconverter.convert(code_obj.code)
    for const_item in code_obj.const_list:
        if const_item.dtype == 'function':
            convert_label_recursive(const_item.value.code_obj)

if __name__ == '__main__':
    file_name = sys.argv[1]
    with open(file_name, 'r') as program_file:
        program = program_file.read()
        code_obj = msparser.generate_code(program)
        convert_label_recursive(code_obj)
        print('the generated code is:\n{}'.format(code_obj))
        print('==============================================')
        virtual_machine = vm.VirtualMachine()
        virtual_machine.run_code(code_obj)
