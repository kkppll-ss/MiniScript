from value import *


class NameListRecord:
    def __init__(self, lexical_depth: int, name_list=None, prev_record=None):
        if name_list is None:
            name_list = []
        self.lexical_depth = lexical_depth
        self.name_list = name_list
        self.prev_record = prev_record

    def append(self, name: str):
        self.name_list.append(name)

    def index(self, name: str):
        return self.name_list.index(name)

    def __contains__(self, name: str):
        return name in self.name_list

    def __str__(self):
        return str((self.lexical_depth, self.name_list))

    def __repr__(self):
        return str(self)


class ScopeManager:
    def __init__(self):
        self._name_list_records = [NameListRecord(0)]
        self._const_list_stack = [[]]
        self._current_record = self._name_list_records[-1]
        self._current_lexical_depth = 0

    @property
    def current_lexical_depth(self):
        return self._current_lexical_depth

    @property
    def current_name_list(self):
        return self._current_record.name_list

    @property
    def current_const_list(self):
        return self._const_list_stack[-1]

    @property
    def current_list(self):
        return self.current_name_list, self.current_const_list

    def new_scope(self, name_list=None):
        if name_list is None:
            name_list = []
        self._current_lexical_depth += 1
        new_record = NameListRecord(self.current_lexical_depth, name_list, self._current_record)
        self._name_list_records.append(new_record)
        self._current_record = self._name_list_records[-1]
        self._const_list_stack.append([])

    def append_name(self, name: str):
        self._current_record.append(name)

    def append_const(self, const: Value):
        self.current_const_list.append(const)

    def contains_name(self, name: str):
        record = self._current_record
        while record and name not in record:
            record = record.prev_record
        return record is not None

    def contains_const(self, const: Value):
        return const in self.current_const_list

    def find_name(self, name: str):
        record = self._current_record
        while record:
            if name in record:
                return record.lexical_depth, record.index(name)
            else:
                record = record.prev_record
        raise KeyError('the name {} does not exist!'.format(name))

    def find_const(self, const: Value):
        return self.current_const_list.index(const)

    def exit_scope(self):
        self._current_record = self._current_record.prev_record
        self._current_lexical_depth = self._current_record.lexical_depth
        self._const_list_stack.pop()
