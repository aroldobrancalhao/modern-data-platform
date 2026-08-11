locals {

  resource_prefix = lower(
    format(
      "%s-%s-%s",
      var.project_name,
      var.resource_name,
      var.environment
    )
  )

  bucket_name = lower(
    format(
      "%s-%s",
      local.resource_prefix,
      var.account_id
    )
  )

  # Glue database names can't use hyphens (Athena/Glue naming rules) --
  # same resource_prefix, underscore-joined instead. Added for the
  # "mdp-" hardcoded-name portability pass (bronze/silver/gold Glue
  # catalog databases), see docs/architecture/roadmap-next-steps.md.
  resource_prefix_underscore = replace(local.resource_prefix, "-", "_")

  glue_database = lower(
    format(
      "%s_glue_%s",
      var.project_name,
      var.environment
    )
  )

  athena_database = lower(
    format(
      "%s_athena_%s",
      var.project_name,
      var.environment
    )
  )

  databricks_role = lower(
    format(
      "%s-databricks-role-%s",
      var.project_name,
      var.environment
    )
  )

  cloudwatch_prefix = format(
    "/%s/%s",
    var.project_name,
    var.environment
  )
}