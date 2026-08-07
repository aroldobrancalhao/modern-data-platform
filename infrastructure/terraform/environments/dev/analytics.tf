##########################################################
# Analytics
##########################################################

module "athena" {

  source = "../../modules/analytics/athena"

  workgroup_name = "mdp-athena-dev"

  # Moved to a dedicated staging bucket (module.athena_staging,
  # storage.tf) -- see that module's comment for why. Only the query
  # results/staging location moves; Gold table data (dbt's
  # `s3_data_dir`, CTAS LOCATION) stays under the main datalake
  # bucket's gold/ prefix, untouched.
  results_bucket = module.athena_staging.bucket_name

  results_prefix = ""

  # Explicit true (matches the pre-existing hardcoded value, no
  # behavior change) -- this workgroup is the one ad-hoc/external BI
  # tools (Metabase, Power BI) query against, so its origin/governance
  # reasoning (undocumented -- see roadmap-next-steps.md) is left
  # untouched rather than assumed safe to change.
  enforce_output_location = true

  tags = local.default_tags
}

##########################################################
# Athena Workgroup -- dbt build (internal only)
##########################################################
#
# Separate workgroup for dbt's own CTAS builds, not exposed to any BI
# tool -- enforce_output_location=false here (unlike mdp-athena-dev
# above) is what lets dbt-athena's external_location config actually
# land in the generated DDL (see create_table_as.sql's
# `not work_group_output_location_enforced` check) -- without this,
# Gold tables silently land under {output_location}/tables/{uuid}/
# instead of gold/{schema}/{table}/, which is what originally sent
# this investigation down the wrong path (a workgroup enforcing an
# output location under gold/ would still hit the same fallback, not
# the readable schema_table path). Same read/write-path-isolation
# reasoning as module.athena_staging in storage.tf: a workgroup that
# only the trusted, internal dbt process ever touches (via the
# `dbt_build` target in ~/.dbt/profiles.yml) can safely run without
# workgroup-level enforcement, without weakening the ad-hoc/BI
# workgroup at all.

module "athena_dbt_build" {

  source = "../../modules/analytics/athena"

  workgroup_name = "mdp-athena-dbt-dev"

  enforce_output_location = false

  results_bucket = module.athena_staging.bucket_name

  results_prefix = "dbt-build/"

  tags = local.default_tags
}