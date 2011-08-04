import os
import sys
import subprocess
import tempfile
import time


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES = ['keystone.db',
              'keystone.token.db',
              'ldap.db']


def execute(cmd, raise_error=True):
    """
    Executes a command in a subprocess. Returns a tuple
    of (exitcode, out, err), where out is the string output
    from stdout and err is the string output from stderr when
    executing the command.

    :param cmd: Command string to execute
    :param raise_error: If returncode is not 0 (success), then
                        raise a RuntimeError? Default: True)
    """

    env = os.environ.copy()

    # Make sure that we use the programs in the
    # current source directory's bin/ directory.
    env['PATH'] = os.path.join(os.getcwd(), 'bin') + ':' + env['PATH']
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               env=env)
    result = process.communicate()
    (out, err) = result
    exitcode = process.returncode
    if process.returncode != 0 and raise_error:
        msg = "Command %(cmd)s did not succeed. Returned an exit "\
              "code of %(exitcode)d."\
              "\n\nSTDOUT: %(out)s"\
              "\n\nSTDERR: %(err)s" % locals()
        raise RuntimeError(msg)
    return exitcode, out, err


def remove_test_files():
    """
    Remove any test databases or files that may have
    been left around from a previous test run.
    """
    for fname in TEST_FILES:
        fpath = os.path.join(TEST_DIR, fname)
        if os.path.exists(fpath):
            print "Removing test file %s" % fname
            os.unlink(fpath)

def construct_conf_file(conf_fp):
    template_fpath = os.path.join(TEST_DIR, 'etc', 'keystone.conf.template')
    conf_contents = open(template_fpath).read()
    conf_contents = conf_contents % {'test_dir': TEST_DIR}
    conf_fp.write(conf_contents)
    conf_fp.flush()


if __name__ == '__main__':

    remove_test_files()
    
    try:
        # Create a configuration file to supply to the keystone
        # server for the test run
        with tempfile.NamedTemporaryFile() as conf_fp:
            construct_conf_file(conf_fp)

            # Populate the test database
            print "Populating registry and token databases"
            exitcode, out, err = execute('sampledata.sh -c %s' % conf_fp.name)
            
            # run the keystone server
            print "Starting Keystone server"
            server = subprocess.Popen([os.path.join(TEST_DIR,
                                                    '../../bin/keystone'),
                                       conf_fp.name])
            
            # blatent hack.
            time.sleep(3)
            if server.poll() is not None:
                print >> sys.stderr, 'Failed to start server'
                sys.exit(-1)
            
            try:
                # run unit tests
                print "Running unit tests"
                subprocess.check_call(
                    ['python', os.path.join(TEST_DIR, 'unit/test_keystone.py')])
                
                # run system tests
                print "Running system tests"
                exitcode, out, err = execute('unit2 discover keystone.test.system')
            finally:
                #kill the keystone server
                print "Stopping Keystone server"
                server.kill()
    finally:
        remove_test_files()
