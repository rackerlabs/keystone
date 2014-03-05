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
    """Provides a simple framework for writing AST-based checks.

    Subclasses should implement visit_* methods like any other AST visitor
    implementation. When they detect an error for a particular node the
    method should call ``self.add_error(offending_node)``. Details about
    where in the code the error occured will be pulled from the node
    object.

    Subclasses should also provide a class variable named CHECK_DESC to
    be used for the human readable error message.

    """

    def __init__(self, tree, filename):
        self._tree = tree
        self._errors = []

    def run(self):
        """Called automatically by pep8."""
        self.visit(self._tree)
        return self._errors

    def add_error(self, node):
        """Add an error caused by a node to the list of errors for pep8."""
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


def block_comments_begin_with_a_space(physical_line, tokens, line_number):
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


class NeedsAssertIsNone(BaseASTChecker):
    """Ensures that code does not use a None with assertEqual."""

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
    register(block_comments_begin_with_a_space)
    register(NeedsAssertIsNone)
