from unittest.mock import Mock

import pytest

from foo.lib.config import ConfigLoader, ConfigLoaderException


def reset_config_loader_singleton():
    ConfigLoader._instance = None
    ConfigLoader._instance_ready = False


def test_load(monkeypatch):
    reset_config_loader_singleton()
    monkeypatch.setenv('VAR3', 'not bar')
    cfg_loader = ConfigLoader(defaults={'VAR0': 'default value 0',
                                        'VAR1': 'default value 1'})
    config = cfg_loader.load('test/foo/lib/config/config.yaml')
    assert config._config == {'VAR0': 'fizz',
                              'VAR1': 'default value 1',
                              'VAR2': 'foo',
                              'VAR3': 'not bar'}
    assert config.source == 'test/foo/lib/config/config.yaml'


def test_load_missing():
    reset_config_loader_singleton()
    cfg_loader = ConfigLoader()
    with pytest.raises(ConfigLoaderException):
        cfg_loader.load('test/foo/lib/config/missing-config.yaml')


def test_is_a_singleton():
    reset_config_loader_singleton()
    assert ConfigLoader(defaults={'VAR0': 'default value 0'}) is ConfigLoader()


def test_load_from_s3(monkeypatch):
    reset_config_loader_singleton()
    monkeypatch.setenv('VAR1', 'not bar')

    mock_file = Mock(autospec='read')
    mock_file.read.return_value = 'prod'
    mock_open = Mock()
    mock_open.return_value = mock_file
    monkeypatch.setattr('builtins.open', mock_open)
    mock_s3_loader = Mock()
    mock_s3_loader.return_value = {'VAR0': 'foo',
                                   'VAR1': 'bar'}
    monkeypatch.setattr(ConfigLoader, '_s3_loader', mock_s3_loader)
    cfg_loader = ConfigLoader()
    config = cfg_loader.load('some/s3/path.yaml')
    assert config._config == {'VAR0': 'foo',
                              'VAR1': 'not bar'}
    assert config.source == 'some/s3/path.yaml'
