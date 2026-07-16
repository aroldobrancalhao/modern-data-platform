terraform {
  backend "s3" {
    bucket = "mdp-tfstate-857854758128"
    key    = "bootstrap/terraform.tfstate"
    region = "sa-east-1"
  }
}