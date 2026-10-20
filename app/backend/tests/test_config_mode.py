"""Tests for the DEPLOY_MODE local/aws configuration switch (config.py)."""


def test_local_mode_is_default(config_in_mode):
    cfg = config_in_mode("local")
    assert cfg.IS_AWS is False
    assert cfg.DEPLOY_MODE == "local"


def test_local_mode_admin_defaults(config_in_mode):
    cfg = config_in_mode("local", ADMIN_USERNAME=None, ADMIN_PASSWORD=None)
    user, pw = cfg.get_admin_credentials()
    assert user == "admin"
    assert pw == "changeme"


def test_local_mode_admin_env_override(config_in_mode):
    cfg = config_in_mode("local", ADMIN_USERNAME="parent", ADMIN_PASSWORD="s3cret")
    assert cfg.get_admin_credentials() == ("parent", "s3cret")


def test_local_mode_jwt_from_env(config_in_mode):
    cfg = config_in_mode("local", SECRET_KEY="local-dev-secret")
    assert cfg.get_jwt_secret() == "local-dev-secret"


def test_local_summary_shape(config_in_mode):
    cfg = config_in_mode("local")
    s = cfg.summary()
    assert s["mode"] == "local"
    assert s["uploads_backend"] == "local"
    assert s["secrets_source"] == "env"


def test_aws_mode_flag(config_in_mode):
    cfg = config_in_mode("aws")
    assert cfg.IS_AWS is True


def test_aws_mode_requires_admin_secret_arn(config_in_mode):
    cfg = config_in_mode("aws", ADMIN_SECRET_ARN=None)
    try:
        cfg.get_admin_credentials()
        raise AssertionError("expected RuntimeError when ADMIN_SECRET_ARN unset")
    except RuntimeError as e:
        assert "ADMIN_SECRET_ARN" in str(e)


def test_aws_mode_requires_jwt_secret_arn(config_in_mode):
    cfg = config_in_mode("aws", JWT_SECRET_ARN=None)
    try:
        cfg.get_jwt_secret()
        raise AssertionError("expected RuntimeError when JWT_SECRET_ARN unset")
    except RuntimeError as e:
        assert "JWT_SECRET_ARN" in str(e)
