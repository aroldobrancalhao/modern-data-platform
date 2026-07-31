from __future__ import annotations

import boto3

from integrations.aws.config import AwsSettings
from integrations.aws.core.aws_context import AwsContext


def test_aws_settings_region_defaults_to_none() -> None:
    assert AwsSettings().region is None


def test_session_does_not_force_a_region_when_settings_use_defaults() -> None:
    context = AwsContext(AwsSettings())
    baseline = boto3.Session()

    assert context.session.region_name == baseline.region_name


def test_session_does_not_force_a_profile_when_settings_use_defaults() -> None:
    context = AwsContext(AwsSettings())
    baseline = boto3.Session()

    assert context.session.profile_name == baseline.profile_name


def test_session_uses_an_explicit_region_override() -> None:
    context = AwsContext(AwsSettings(region="eu-west-1"))

    assert context.session.region_name == "eu-west-1"
