"""Unit tests for Cloud Storage signing behavior."""

from types import SimpleNamespace
from unittest.mock import Mock

from services import storage


def test_signed_url_uses_cloud_platform_scoped_adc(monkeypatch) -> None:
    blob = Mock()
    blob.generate_signed_url.return_value = "https://signed.example/video.mp4"
    bucket = Mock()
    bucket.blob.return_value = blob
    client = Mock()
    client._credentials = SimpleNamespace(signer=None)
    client.bucket.return_value = bucket

    signing_credentials = SimpleNamespace(
        valid=False,
        service_account_email="runtime@example.iam.gserviceaccount.com",
        token="cloud-platform-token",
        refresh=Mock(),
    )
    default_credentials = Mock(return_value=(signing_credentials, "gleamail"))

    monkeypatch.setattr(storage, "_get_client", lambda: client)
    monkeypatch.setattr(storage.google.auth, "default", default_credentials)

    url = storage.generate_signed_url("gs://movescore-temp/final/video.mp4")

    assert url == "https://signed.example/video.mp4"
    default_credentials.assert_called_once_with(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    signing_credentials.refresh.assert_called_once()
    blob.generate_signed_url.assert_called_once_with(
        version="v4",
        expiration=storage.datetime.timedelta(hours=1),
        method="GET",
        service_account_email="runtime@example.iam.gserviceaccount.com",
        access_token="cloud-platform-token",
    )
