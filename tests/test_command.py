from flit.common import VCSError, NoVersionError, NoDocstringError
from subprocess import Popen, PIPE, STDOUT
from unittest.mock import patch, MagicMock
import sys
import pytest

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
               stdout=PIPE, stderr=PIPE)
    out, _ = p.communicate()
    assert out.decode('utf-8', 'replace').strip() == version


def test_flit_init():
    from flit.subcommand import init
    with patch('flit.subcommand.init.TerminalIniter') as ptch:
        exitcode = init.run(None)
        ptch().initialise.assert_called_with()
        assert exitcode == 0


def test_flit_build():
    from flit.subcommand import build
    mock_args = MagicMock(ini_file='foo', format='bar')
    with patch('flit.subcommand.build.main') as ptch:
        exitcode = build.run(mock_args)
        ptch.assert_called_with('foo', formats=set('bar'))
        assert exitcode == 0


@pytest.mark.parametrize('error_instance', [
    NoDocstringError('whoops'),
    VCSError('whoops', 'dirname'),
    NoVersionError('whoops'),
])
def test_flit_build_error(error_instance):
    from flit.subcommand import build
    mock_args = MagicMock(ini_file='foo', format='bar')
    with patch('flit.subcommand.build.main') as ptch:
        ptch.side_effect = error_instance
        exitcode = build.run(mock_args)
        assert exitcode != 0


def test_flit_install():
    from flit.subcommand import install
    # Set up simple sentinels. We don't care about the type. We only want to
    # make sure the correct argument-parser values are passed to the correct
    # constructor args.
    mock_args = MagicMock(
        ini_file='inifile',
        user='user',
        python='python',
        symlink='symlink',
        deps='deps',
        extras='extras',
        pth_file='pth',
    )
    with patch('flit.subcommand.install.Installer') as ptch:
        exitcode = install.run(mock_args)
        ptch.assert_called_with(
            'inifile',
            user='user',
            python='python',
            symlink='symlink',
            deps='deps',
            extras='extras',
            pth='pth'
        )
        ptch().install.assert_called_with()
        assert exitcode == 0


@pytest.mark.parametrize('error_instance', [
    NoDocstringError('whoops'),
    NoVersionError('whoops')
])
def test_flit_install_error(error_instance):
    from flit.subcommand import install
    mock_args = MagicMock(ini_file='foo', format='bar')
    with patch('flit.subcommand.install.Installer') as ptch:
        ptch.side_effect = error_instance
        exitcode = install.run(mock_args)
        assert exitcode != 0


def test_flit_installfrom():
    from flit.subcommand import installfrom
    # Set up simple sentinels. We don't care about the type. We only want to
    # make sure the correct argument-parser values are passed to the correct
    # constructor args.
    mock_args = MagicMock(
        location='location',
        user='user',
        python='python',
    )
    with patch('flit.subcommand.installfrom.installfrom') as ptch:
        ptch.return_value = 0
        exitcode = installfrom.run(mock_args)
        ptch.assert_called_with(
            'location',
            user='user',
            python='python',
        )
        assert exitcode == 0


def test_flit_publish():
    from flit.subcommand import publish
    # Set up simple sentinels. We don't care about the type. We only want to
    # make sure the correct argument-parser values are passed to the correct
    # constructor args.
    mock_args = MagicMock(
        ini_file='ini_file',
        repository='repository',
        format='format',
    )
    with patch('flit.subcommand.publish.main') as ptch:
        exitcode = publish.run(mock_args)
        ptch.assert_called_with(
            'ini_file',
            'repository',
            formats=set('format')
        )
        assert exitcode == 0
