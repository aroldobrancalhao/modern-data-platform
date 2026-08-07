# IAM User Module

For principals that cannot assume a role (external tools without
native AWS SigV4/STS support -- e.g. a containerized BI tool or a
desktop app's ODBC driver), unlike `modules/security/iam` (role-based,
for AWS services that assume a role).

Creates:

- IAM User
- IAM Access Key (long-lived, for the User)
- IAM Policy
- IAM User Policy Attachment

Outputs:

- user_name
- user_arn
- policy_arn
- policy_name
- access_key_id
- secret_access_key (sensitive)
