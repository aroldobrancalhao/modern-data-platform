from __future__ import annotations

from botocore.exceptions import ClientError

from integrations.aws.storage.error_mapper import AwsStorageErrorMapper


def client_error(code: str) -> ClientError:

    return ClientError(
        error_response={
            "Error": {
                "Code": code,
            }
        },
        operation_name="HeadObject",
    )


def test_is_not_found_for_404() -> None:

    assert AwsStorageErrorMapper.is_not_found(
        client_error("404")
    )


def test_is_not_found_for_no_such_key() -> None:

    assert AwsStorageErrorMapper.is_not_found(
        client_error("NoSuchKey")
    )


def test_is_not_found_for_not_found() -> None:

    assert AwsStorageErrorMapper.is_not_found(
        client_error("NotFound")
    )


def test_is_not_found_for_other_errors() -> None:

    assert not AwsStorageErrorMapper.is_not_found(
        client_error("AccessDenied")
    )