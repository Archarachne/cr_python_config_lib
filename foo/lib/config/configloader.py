import os
import tempfile
import boto3
import botocore
import yaml

from typing import Optional


TEST_ENV = 'test'
PROD_ENV = 'prod'


class ConfigLoaderException(Exception):
    pass


class Config:

    def __init__(self, config: dict, source: str):
        self._config = config
        self._source = source

    def __repr__(self):
        return f'{{config: {self._config} source: {self.source}}}'

    def __str__(self):
        return f'Config(config={self._config!r} source={self.source!r})'

    def __getattr__(self, name):
        return self._config[name]

    def __getitem__(self, name):
        return self._config[name]

    @property
    def source(self):
        return self._source

    def get(self, name, default=None):
        return self._config.get(name, default)


class Singleton(type):  # TODO Move it to separate file
    """Singleton implementation"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigLoader(metaclass=Singleton):
    """
    Loads configuration files.

    Source of the config depends on the currently set environment (either
    'test' or 'prod', as dictated by the *.env* file.
    """

    S3_BUCKET: Optional[str] = os.getenv('S3_BUCKET', default=None)
    _instance_ready = False
    _config: Optional[Config] = None

    def __init__(self, defaults: Optional[dict] = None):
        if self._instance_ready:
            return

        env: str = os.getenv('ENVIRONMENT', default='')
        self.defaults = defaults if defaults else {}

        print(f'Current environment is: {env!r}')

        if env == TEST_ENV:
            self._handler = self._local_loader
        elif env == PROD_ENV:
            if not self.S3_BUCKET:
                raise ConfigLoaderException('No S3 bucket defined!')
            self._handler = self._s3_loader
        else:
            raise ConfigLoaderException('No running environment defined!')
        self._instance_ready = True

    def _local_loader(self, path: str) -> dict:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    config = yaml.load(f, Loader=yaml.BaseLoader)
            except IOError:
                raise ConfigLoaderException(f'Error opening {path}')
            if not isinstance(config, dict):
                raise ConfigLoaderException(f'Improperly configured config file')
            return config
        else:
            raise ConfigLoaderException(f'File {path} does not exist')

    def _s3_loader(self, path: str) -> dict:
        try:
            s3 = boto3.client('s3')
            with tempfile.TemporaryFile("wb") as f:
                s3.download_fileobj(self.S3_BUCKET, path, f)
                config = yaml.load(f, Loader=yaml.BaseLoader)
        except botocore.exceptions.NoCredentialsError:
            raise ConfigLoaderException(f'No S3 credentials')
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ConfigLoaderException(f'No such file {path}')
            else:
                raise ConfigLoaderException(f'Could not connect to S3')
        except IOError:
            raise ConfigLoaderException(f'Error when opening {path}')
        if not isinstance(config, dict):
            raise ConfigLoaderException(f'Improperly configured config file')
        return config

    def load(self, path: str) -> Config:
        if self._config:
            return self._config

        config = self._handler(path)

        env = os.environ.copy()
        for key in config:
            if key in env:
                config[key] = env.get(key)

        config = {**self.defaults, **config}

        self._config = Config(config, path)
        return self._config

    def reset(self):
        self._config = None
