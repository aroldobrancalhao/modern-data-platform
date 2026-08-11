# Terraform

Infrastructure as Code for Modern Data Platform's AWS footprint --
Sprint 14. Two independent root modules, a shared module library, one
real environment today (`dev`).

## Layout

```text
infrastructure/terraform/
├── bootstrap/            # Root module #1 -- the Terraform state bucket itself
├── environments/
│   └── dev/               # Root module #2 -- every real platform resource
└── modules/                # Shared, reusable module library (used by environments/dev)
    ├── foundation/naming/   # Consistent resource naming (project-resource-env)
    ├── security/iam/        # IAM Role + Policy pair
    ├── security/iam_user/   # IAM User + Policy + Access Key pair
    ├── storage/datalake/    # S3 bucket (versioning, encryption, public-access-block, folder objects)
    ├── catalog/glue/        # Glue Catalog Database + Crawler
    ├── analytics/athena/    # Athena Workgroup
    └── monitoring/cloudwatch/ # CloudWatch Log Group
```

### `bootstrap/` -- why it's separate

`bootstrap/` creates the S3 bucket (`mdp-tfstate-*`) that **every**
root module's own state lives in, `environments/dev/` included. It
can't depend on that bucket already existing, so it's its own
independent root module with its own state (`bootstrap/terraform.tfstate`,
in the same bucket, once the bucket itself exists) -- the standard way
to avoid the chicken-and-egg problem of "the thing that manages remote
state needs remote state too."

### `environments/dev/` -- everything real

Every actual platform resource this project runs against AWS: the
data lake bucket, Glue Catalog databases, Athena workgroups, every
IAM identity (`bi_reader`, `airflow_ingest`, `bronze_consumer`,
`dbt_gold`, the Databricks Unity Catalog role), and the CloudWatch log
groups (`airflow`, `platform`, `databricks`, `terraform`). One file
per concern (`storage.tf`, `catalog.tf`, `analytics.tf`, `security.tf`,
`monitoring.tf`, `foundation.tf` for the naming module instances),
`outputs.tf` for every value other tooling reads (see
`scripts/export-terraform-outputs.sh`), `locals.tf` for shared tags.

Only `dev` exists today -- no `staging`/`prod` sibling. If a second
real environment is ever needed, it's a new `environments/<name>/`
directory following the same shape (its own `backend-<name>.hcl`, its
own `terraform.tfvars`), not a parameter on this one.

## Module naming convention

Every real AWS resource name in `environments/dev/` is built from
`modules/foundation/naming`, not a hardcoded string --
`"${var.project_name}-${resource_name}-${var.environment}"` (or the
`_`-joined variant, `resource_prefix_underscore`, for Glue database
names, which can't contain hyphens). One `module "naming_x"` instance
per named resource, all declared together in `foundation.tf`. This is
what makes the whole environment portable to a different
`project_name`/`environment` without touching a single resource block
-- see `docs/architecture/roadmap-next-steps.md` for the investigation
that got every resource onto this pattern (all but 2: a Terraform
`backend {}` block can't reference `var.*` at all, a hard language
restriction -- see "Backend configuration" below for how those 2 are
handled instead).

## Getting started

```bash
cd infrastructure/terraform/environments/dev  # or bootstrap/

terraform init -backend-config=backend-dev.hcl

terraform plan   # terraform.tfvars is auto-loaded -- no -var flags needed
```

### Backend configuration

Both root modules' `backend.tf` is a deliberately **empty**
`backend "s3" {}` block -- real values (`bucket`, `key`, `region`,
`use_lockfile`) live in a sibling `backend-dev.hcl` file instead
(*partial backend configuration*, Terraform's own idiomatic answer to
"a backend block can't use variables"). `terraform init` alone is
**not enough** -- it needs the config file explicitly:

```bash
terraform init -backend-config=backend-dev.hcl
```

Re-run the same command (`-reconfigure` if switching between an
already-initialized different config) any time the backend config
itself changes. This does not touch or migrate state when the
underlying bucket/key/region are unchanged -- confirmed live via a
real `terraform state list` diff before/after, see the roadmap entry
this section is drawn from.

Both `backend-dev.hcl` files set `use_lockfile = true` -- native S3
state locking (a real `.tflock` object, S3 conditional writes),
generally available since Terraform 1.11. **Not DynamoDB** -- that
mechanism is officially deprecated as of the Terraform version this
project runs (1.15.8) and needs zero extra AWS resources here. A
concurrent `plan`/`apply` against the same state fails fast with a
real `PreconditionFailed` lock error instead of racing -- validated
live, not assumed (see the roadmap entry).

### Variables (`terraform.tfvars`)

Both roots have a committed `terraform.tfvars` -- one of the two
filenames (`terraform.tfvars`, `*.auto.tfvars`) Terraform loads
automatically on every `plan`/`apply`, no `-var`/`-var-file` flag
needed. None of the values in either file are credentials (evaluated
deliberately, not assumed -- see each file's own comment for the
`account_id` question specifically). A real secret never belongs in a
`.tfvars` file in this project -- see "Secrets" below.

To add a resource that needs a new variable: add it to the relevant
`variables.tf`, then to both `terraform.tfvars` files if it's a value
every real command needs (or leave it out and rely on the variable's
own `default`, if one exists and is safe -- see
`databricks_uc_external_id` for that pattern).

### Secrets

Real credentials (IAM access keys, the Databricks PAT, the Telegram
bot token, ...) never flow through `.tfvars`. The pattern this project
uses everywhere: a sensitive Terraform *output* (`sensitive = true`,
e.g. `bi_reader_secret_access_key`), read once with
`terraform output -raw <name>` -- captured directly into a shell
variable and written straight to `infrastructure/docker/.env`
(gitignored), **never printed to a terminal or committed** -- see
`docs/architecture/roadmap-next-steps.md` for several real examples of
this exact flow, including why a bare `terraform output -raw` command
was blocked by this project's own tooling once for printing a secret
directly.

## Provisioned but never wired -- Databricks

The `databricks_uc_role_arn` output and the Unity Catalog IAM role
(`aws_iam_role.databricks_uc`, `security.tf`) are provisioned here,
but the actual Databricks workspace/Unity Catalog storage credential
that references them is not itself Terraform-managed (Databricks
authentication for this project is deliberately out of Terraform's
scope -- see `infrastructure/databricks/` for the Databricks Asset
Bundle that owns Jobs/environments instead).

## More context

`docs/architecture/roadmap-next-steps.md` is where every real decision,
investigation, and validated `plan`/`apply` behind this directory's
current shape is actually recorded -- this file is a map, that one is
the log. `docs/architecture/ADR-003-cloud-strategy.md` covers the
cloud-agnostic reasoning one level up from Terraform specifics.
