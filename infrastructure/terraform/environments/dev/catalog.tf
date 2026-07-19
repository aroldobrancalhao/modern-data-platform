##########################################################
# Data Catalog
##########################################################

module "glue_bronze" {

  source = "../../modules/catalog/glue"

  database_name = "mdp_bronze_dev"

  crawler_name = "mdp-bronze-crawler-dev"

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "bronze/"

  tags = local.default_tags
}

module "glue_silver" {

  source = "../../modules/catalog/glue"

  database_name = "mdp_silver_dev"

  crawler_name = "mdp-silver-crawler-dev"

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "silver/"

  tags = local.default_tags
}

module "glue_gold" {

  source = "../../modules/catalog/glue"

  database_name = "mdp_gold_dev"

  crawler_name = "mdp-gold-crawler-dev"

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "gold/"

  tags = local.default_tags
}