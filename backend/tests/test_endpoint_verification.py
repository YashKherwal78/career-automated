from unittest.mock import MagicMock, patch
from src.ingestion.endpoint_verification import is_endpoint_verified, mark_endpoint_verified


@patch("src.ingestion.endpoint_verification.get_connection")
def test_is_endpoint_verified_true_when_status_verified(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"status": "VERIFIED"}
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert is_endpoint_verified("acme.com", "workday") is True


@patch("src.ingestion.endpoint_verification.get_connection")
def test_is_endpoint_verified_false_when_no_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert is_endpoint_verified("acme.com", "workday") is False


@patch("src.ingestion.endpoint_verification.get_connection")
def test_mark_endpoint_verified_upserts_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    mark_endpoint_verified("acme.com", "workday", "https://acme.wd1.myworkdayjobs.com/careers")

    assert mock_conn.execute.called
    assert mock_conn.commit.called
