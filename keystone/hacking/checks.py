# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ast


class BaseASTChecker(ast.NodeVisitor):

    def __init__(self, tree, filename):
        self._tree = tree
        self._errors = []

    def run(self):
        self.visit(self._tree)
        return self._errors

    def add_error(self, node):
        error = (node.lineno, node.col_offset, self.CHECK_DESC, self.__class__)
        self._errors.append(error)


class CheckForMutableDefaultArgs(BaseASTChecker):
    """Checks for the use of mutable objects as function/method defaults.

    """

    CHECK_DESC = 'K001 Using mutable as a function/method default'
    MUTABLES = (
        ast.List, ast.ListComp,
        ast.Dict, ast.DictComp,
        ast.Set, ast.SetComp)

    def visit_FunctionDef(self, node):
        for arg in node.args.defaults:
            if isinstance(arg, self.MUTABLES):
                self.add_error(arg)

        super(CheckForMutableDefaultArgs, self).generic_visit(node)


def space_after_comment_hash(physical_line, tokens, line_number):
    """There should be a single space after the # of block comments.

    There is already a check in pep8 that enforces this rule for
    inline comments.

    Okay: # this is a comment
    K102: #this is a comment
    K102: #  this is a comment

    """
    MESSAGE = "K102 block comments should start with '# '"

    # shebangs are OK
    if line_number == 1 and physical_line.startswith('#!'):
        return

    text = physical_line.strip()
    if text.startswith('#'):  # look for block comments
        if len(text) > 1 and not text[1].isspace():
            return physical_line.index('#'), MESSAGE


def use_single_quotes_where_possible(logical_line, tokens):
    print logical_line
    print tokens
    return []
    pass


class use_single_quotes_where_possible(BaseASTChecker):

    def visit_Str(self, node):
        print vars(node)


class NeedsAssertIsNone(BaseASTChecker):
    CHECK_DESC = 'K003 Use assertIsNone when comparing against None'

    def visit_Call(self, node):
        # NOTE(dstanek): I wrote this in a verbose way to make it easier to
        # read for those that have little experience with Python's AST.

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'assertEqual':
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == 'None':
                        self.add_error(node)

        super(NeedsAssertIsNone, self).generic_visit(node)


def factory(register):
    register(CheckForMutableDefaultArgs)
    register(space_after_comment_hash)
    register(NeedsAssertIsNone)
