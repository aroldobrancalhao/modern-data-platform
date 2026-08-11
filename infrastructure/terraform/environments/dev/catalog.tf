##########################################################
# Data Catalog
##########################################################

module "glue_bronze" {

  source = "../../modules/catalog/glue"

  database_name = module.naming_glue_bronze.resource_prefix_underscore

  crawler_name = module.naming_glue_bronze_crawler.resource_prefix

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "bronze/"

  tags = local.default_tags
}

module "glue_silver" {

  source = "../../modules/catalog/glue"

  database_name = module.naming_glue_silver.resource_prefix_underscore

  crawler_name = module.naming_glue_silver_crawler.resource_prefix

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "silver/"

  tags = local.default_tags
}

module "glue_gold" {

  source = "../../modules/catalog/glue"

  database_name = module.naming_glue_gold.resource_prefix_underscore

  crawler_name = module.naming_glue_gold_crawler.resource_prefix

  crawler_role_arn = module.glue_iam.role_arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "gold/"

  tags = local.default_tags
}