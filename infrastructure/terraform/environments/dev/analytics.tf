##########################################################
# Analytics
##########################################################

module "athena" {

  source = "../../modules/analytics/athena"

  workgroup_name = "mdp-athena-dev"

  results_bucket = module.datalake.bucket_name

  results_prefix = "athena/"

  tags = local.default_tags
}