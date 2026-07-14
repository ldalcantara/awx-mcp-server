"""Unit tests for storage.vault_integration (no live vault).

The module is an explicit v2.0.0 placeholder: the factory and data classes are
real, while every provider method raises NotImplementedError. These tests lock
that contract so a partial implementation (or an accidental silent no-op) can't
slip in unnoticed — a security-sensitive module must fail loudly, not pretend.
"""

import pytest

from awx_mcp_server.storage.vault_integration import (
    VAULT_PROVIDERS,
    AWSSecretsManagerProvider,
    AWXCredentials,
    AzureKeyVaultProvider,
    BaseVaultProvider,
    GoogleSecretManagerProvider,
    HashiCorpVaultProvider,
    VaultAccessDeniedError,
    VaultAuthenticationError,
    VaultCredentialsNotFoundError,
    VaultProvider,
    create_vault_provider,
)

REGISTERED = [
    (VaultProvider.HASHICORP_VAULT, HashiCorpVaultProvider),
    (VaultProvider.AWS_SECRETS_MANAGER, AWSSecretsManagerProvider),
    (VaultProvider.AZURE_KEY_VAULT, AzureKeyVaultProvider),
    (VaultProvider.GOOGLE_SECRET_MANAGER, GoogleSecretManagerProvider),
]
UNREGISTERED = [
    VaultProvider.KUBERNETES_SECRETS,
    VaultProvider.GITHUB_SECRETS,
    VaultProvider.CYBERARK,
    VaultProvider.ONEPASSWORD,
]


@pytest.mark.parametrize("ptype,cls", REGISTERED)
def test_factory_builds_registered_providers(ptype, cls):
    provider = create_vault_provider(ptype, {"url": "https://vault.test"})
    assert isinstance(provider, cls)
    assert isinstance(provider, BaseVaultProvider)
    assert provider.config == {"url": "https://vault.test"}


@pytest.mark.parametrize("ptype", UNREGISTERED)
def test_factory_rejects_unregistered_providers(ptype):
    with pytest.raises(ValueError, match="Unsupported vault provider"):
        create_vault_provider(ptype, {})


def test_registry_matches_enum_subset():
    # Every registry key is a valid enum member and maps to a Base subclass.
    for ptype, cls in VAULT_PROVIDERS.items():
        assert isinstance(ptype, VaultProvider)
        assert issubclass(cls, BaseVaultProvider)


@pytest.mark.parametrize("ptype,cls", REGISTERED)
async def test_stub_methods_fail_loudly(ptype, cls):
    """Placeholder providers must raise, never silently return credentials."""
    provider = create_vault_provider(ptype, {})
    creds = AWXCredentials(awx_url="https://awx.test")
    with pytest.raises(NotImplementedError):
        await provider.get_credentials("user@test")
    with pytest.raises(NotImplementedError):
        await provider.update_credentials("user@test", creds)
    with pytest.raises(NotImplementedError):
        await provider.delete_credentials("user@test")
    with pytest.raises(NotImplementedError):
        await provider.health_check()


def test_awx_credentials_defaults():
    creds = AWXCredentials(awx_url="https://awx.test")
    assert creds.awx_url == "https://awx.test"
    assert creds.awx_token is None
    assert creds.awx_username is None
    assert creds.awx_password is None
    assert creds.environment == "production"
    assert creds.metadata is None


def test_vault_exceptions_are_exceptions():
    for exc in (
        VaultAuthenticationError,
        VaultAccessDeniedError,
        VaultCredentialsNotFoundError,
    ):
        assert issubclass(exc, Exception)
