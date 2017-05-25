import sys

import csparser
import vm
import assembler
import pickle


def compile(file_name: str, output_name: str):
    with open(file_name, 'r') as program_file:
        program = program_file.read()
        code = csparser.generate_code(program)
        code['co_code'] = assembler.assemble(code['co_code'])
        print('the generated code is {}'.format(code))
        output = open(output_name, 'wb')
        pickle.dump(code, output)


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
