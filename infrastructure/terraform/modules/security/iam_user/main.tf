resource "aws_iam_user" "this" {

  name = var.user_name

  tags = var.tags
}

resource "aws_iam_access_key" "this" {

  user = aws_iam_user.this.name
}

resource "aws_iam_policy" "this" {

  name = var.policy_name

  description = var.description

  policy = var.policy

  tags = var.tags
}

resource "aws_iam_user_policy_attachment" "this" {

  user = aws_iam_user.this.name

  policy_arn = aws_iam_policy.this.arn
}
