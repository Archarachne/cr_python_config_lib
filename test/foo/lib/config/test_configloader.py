from unittest.mock import Mock

import pytest

from foo.lib.config import ConfigLoader, ConfigLoaderException


@pytest.fixture(autouse=True)
def reset_config_loader_singleton(monkeypatch):
    ConfigLoader._instances = {}
    ConfigLoader._instance_ready = False
    monkeypatch.setenv('ENVIRONMENT', 'test')


def test_load(monkeypatch):
    source_path = 'test/foo/lib/config/config.yaml'
    monkeypatch.setenv('VAR3', 'not bar')

    cfg_loader = ConfigLoader(defaults={'VAR0': 'default value 0',
                                        'VAR1': 'default value 1'})
    config = cfg_loader.load(source_path)
    assert config._config == {'VAR0': 'fizz',
                              'VAR1': 'default value 1',
                              'VAR2': 'foo',
                              'VAR3': 'not bar'}
    assert config.source == source_path


def test_load_missing():
    cfg_loader = ConfigLoader()
    with pytest.raises(ConfigLoaderException) as cle:
        cfg_loader.load('test/foo/lib/config/missing-config.yaml')
    assert 'does not exist' in str(cle.value)


def test_failed_load():
    cfg_loader = ConfigLoader()

    with pytest.raises(ConfigLoaderException) as cle:
        cfg_loader.load('test/foo/lib/config/failed-config.yaml')
    assert 'Improperly configured' in str(cle.value)

    with pytest.raises(ConfigLoaderException) as cle:
        cfg_loader.load('test/foo/lib/config/empty-config.yaml')
    assert 'Improperly configured' in str(cle.value)


def test_is_a_singleton():
    c1 = ConfigLoader(defaults={'VAR0': 'default value 0'})
    c2 = ConfigLoader()
    assert id(c1) == id(c2)


def test_load_from_s3(monkeypatch):
    source_path = 'some/s3/path.yaml'
    monkeypatch.setenv('VAR1', 'not bar')
    monkeypatch.setenv('ENVIRONMENT', 'prod')
    monkeypatch.setenv('S3_BUCKET', 'prod')

    mock_s3_loader = Mock()
    mock_s3_loader.return_value = {'VAR0': 'foo',
                                   'VAR1': 'bar'}
    monkeypatch.setattr(ConfigLoader, '_s3_loader', mock_s3_loader)
    cfg_loader = ConfigLoader()
    config = cfg_loader.load(source_path)
    assert config.source == source_path


def test_failed_load_from_s3(monkeypatch):
    source_path = 'some/s3/path.yaml'
    monkeypatch.setenv('ENVIRONMENT', 'prod')

    cfg_loader = ConfigLoader()
    with pytest.raises(ConfigLoaderException) as cle:
        config = cfg_loader.load(source_path)
    assert 'No S3 credentials' in str(cle.value)
