#!/usr/bin/env python3
"""
Modern Data Platform

Optional wrapper around `terraform` (environments/dev) that ships the
real plan/apply/destroy output to the `terraform` CloudWatch log group
(module.cloudwatch_terraform, monitoring.tf) -- Sprint 13 close-out.

Design decisions, recorded here rather than left implicit:

- **Name**: terraform_with_cloudwatch_logging.py -- deliberately
  verbose over something like `tf.py`, matching this project's
  existing scripts/run_*.py naming (explicit over terse).
- **Location**: scripts/ -- same place export-terraform-outputs.sh
  (the other Terraform-adjacent operational script) already lives,
  not infrastructure/terraform/ itself (that tree is Terraform
  source, not tooling).
- **Optional, not a replacement**: this project's day-to-day Terraform
  workflow (this exact session included) runs `terraform -chdir=...
  plan/apply` directly, with hand-typed -var flags -- no committed
  .tfvars file exists yet (a separate, tangential gap, not fixed here,
  see roadmap-next-steps.md). This wrapper doesn't change that
  workflow or require it; it's a second, opt-in way to run the exact
  same command when a durable, queryable record of a real plan/apply's
  terminal output is wanted (e.g. before/after a destructive change).
  Terraform's own state already records *what* changed; this fills the
  "what did the terminal actually show" gap, on the same CloudWatch
  timeline as every other log group this project ships to.
- **Auth**: runs under whatever AWS credential the caller's shell
  already has configured for Terraform itself (the personal
  `terraform-admin` key on this local machine, `~/.aws/credentials
  [default]`) -- no new IAM identity or grant needed. Confirmed live:
  that credential already created and destroyed real CloudWatch log
  groups this same session (the glue/athena removal above), so it is
  already broad enough for `logs:CreateLogGroup`/`PutLogEvents` too.
- **CloudWatch unavailable**: NOT swallowed the way the platform
  handler's failures are (see logging_config.py's
  _ship_to_cloudwatch) -- deliberately different trade-off. That
  handler protects a long-running production process (bronze-consumer)
  from crashing over a logging concern. This is a short-lived,
  interactively-run CLI wrapper around a real infrastructure mutation
  -- if CloudWatch shipping is broken, the operator running `terraform
  apply` should see that immediately (it prints to stderr and the
  process still exits with terraform's own real exit code either way,
  it does not fail the terraform run itself over a shipping error) --
  but it's surfaced, not silently degraded to "no audit record and no
  one noticed."

Usage:
    uv run python scripts/terraform_with_cloudwatch_logging.py plan \\
        -var="aws_region=sa-east-1" -var="project_name=mdp" ...
    uv run python scripts/terraform_with_cloudwatch_logging.py apply \\
        -auto-approve -var="aws_region=sa-east-1" ...

Every argument after the script name is passed to `terraform
-chdir=infrastructure/terraform/environments/dev` verbatim -- this
script does not interpret or validate them. Exit code mirrors
terraform's own.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import watchtower

_LOG_GROUP = "/mdp/dev/terraform"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TF_DIR = _REPO_ROOT / "infrastructure" / "terraform" / "environments" / "dev"


def main(argv: list[str]) -> int:
    if not argv:
        print(
            "usage: terraform_with_cloudwatch_logging.py <terraform args...>",
            file=sys.stderr,
        )
        return 2

    logger = logging.getLogger("scripts.terraform_with_cloudwatch_logging")
    logger.setLevel(logging.INFO)
    # Ship-only logger, same reasoning as
    # data_platform.observability.logging_config's own CloudWatch
    # logger -- never hand records to the root logger, this one exists
    # solely to drive the handler below.
    logger.propagate = False

    try:
        handler = watchtower.CloudWatchLogHandler(
            log_group_name=_LOG_GROUP,
            create_log_group=False,
        )
        logger.addHandler(handler)
    except Exception as exc:  # noqa: BLE001 -- see module docstring's "CloudWatch unavailable"
        handler = None
        print(
            f"terraform_with_cloudwatch_logging: CloudWatch shipping unavailable "
            f"({exc!r}) -- running terraform with console output only, no audit "
            f"record for this run.",
            file=sys.stderr,
        )

    command = ["terraform", f"-chdir={_TF_DIR}", *argv]
    command_line = " ".join(command)
    print(f"+ {command_line}")

    if handler is not None:
        logger.info("Running: %s", command_line)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None

    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        print(line)
        if handler is not None and line:
            logger.info(line)

    exit_code = process.wait()

    if handler is not None:
        logger.info("terraform exited with code %d", exit_code)
        # send_interval defaults to 60s -- explicit close() blocks
        # until the queue drains (FLUSH_TIMEOUT) instead of relying on
        # the batch window, so a short plan's output doesn't sit
        # unflushed if this short-lived process exits before the next
        # scheduled batch.
        handler.close()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
