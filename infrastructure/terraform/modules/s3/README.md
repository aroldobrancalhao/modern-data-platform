# S3 Module

Reusable Terraform module responsible for provisioning Amazon S3 buckets.

## Features

- Bucket creation
- Versioning
- Server-side encryption (AES256)
- Public access block
- Optional prevent_destroy
- Optional force_destroy
- Tags support

## Example

```hcl
module "datalake" {
  source = "../../modules/s3"

  bucket_name = "mdp-datalake-dev-857854758128"

  versioning_enabled = true

  prevent_destroy = true

  force_destroy = false

  tags = local.default_tags
}
```