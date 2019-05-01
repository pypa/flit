from subprocess import Popen, PIPE, STDOUT
import sys

def test_flit_help():
    p = Popen([sys.executable, '-m', 'flit', '--help'], stdout=PIPE, stderr=STDOUT)
    out, _ = p.communicate()
    assert 'Build wheel' in out.decode('utf-8', 'replace')

def test_flit_usage():
    p = Popen([sys.executable, '-m', 'flit'], stdout=PIPE, stderr=STDOUT)
    out, _ = p.communicate()
    assert 'Build wheel' in out.decode('utf-8', 'replace')
    assert p.poll() == 1

def test_flit_version():
    import flit
    version = flit.__version__

    p = Popen([sys.executable, '-m', 'flit', 'info', '--version'],
               stdout=PIPE, stderr=STDOUT)
    out, _ = p.communicate()
    assert out.decode('utf-8', 'replace').strip() == version
