import sys
import StringIO


class OutputBuffer():
    """Replaces stdout with a StringIO buffer"""

    def __init__(self):
        """Initialize output buffering"""
        self.buffering = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.stop()
        else:
            raise exc_type, exc_value, traceback

    def start(self):
        """Replace stdout with a buffer"""
        assert not self.buffering

        self.buffering = True
        self.old_stdout = sys.stdout
        sys.stdout = StringIO.StringIO()

    def read(self):
        """Read the current buffer"""
        assert self.buffering

        return sys.stdout.getvalue()

    def read_lines(self):
        """Returns the current buffer as a list

        Excludes the last line, which is empty.
        """
        return self.read().split("\n")[:-1]

    def stop(self):
        """Stop buffering and pass the output along"""
        assert self.buffering

        output = self.read()
        sys.stdout.close()

        sys.stdout = self.old_stdout
        print output
        self.buffering = False

        return output
