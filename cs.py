import sys

import csparser
import pyvm2
import assembler


def main(file_name: str):
    with open(file_name, 'r') as program_file:
        vm = pyvm2.VirtualMachine()
        program = program_file.read()
        code = csparser.generate_code(program)
        code['co_code'] = assembler.assemble(code['co_code'])
        print('the generated code is {}'.format(code))
        vm.run_code(code)

if __name__ == '__main__':
    main(sys.argv[1])
