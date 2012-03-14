import os
import subprocess


def setup(app):
    print "**Autodocumenting from %s" % os.path.abspath(os.curdir)
    subprocess.call('./doc/generate_autodoc_index.sh', shell=True)
