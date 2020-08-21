import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    """Base configuration"""

    TESTING = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET")
    JWT_ACCESS_TOKEN_EXPIRES = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DOMAIN_ROOT = ".meadstats.com"
    APP_DOMAIN = "https://www.meadstats.com"
    API_DOMAIN = "https://api.meadstats.com"

    UNTAPPD_CLIENT_ID = os.environ.get("CLIENT_ID")
    UNTAPPD_CLIENT_SECRET = os.environ.get("CLIENT_SECRET")


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    """Production configuration"""

    DEBUG = False
    SQLALCHEMY_ECHO = False
