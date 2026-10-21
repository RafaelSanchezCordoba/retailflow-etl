# Dedicated app user, scoped only to the raw bucket. No access key is
# created here: an access key secret stored in Terraform state is an
# anti-pattern. Create it manually (Step after apply) and put it in .env.
resource "aws_iam_user" "app" {
  name = "retailflow-app"
}

resource "aws_iam_user_policy" "raw_bucket_access" {
  name = "retailflow-raw-bucket-access"
  user = aws_iam_user.app.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListRawBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.raw.arn
      },
      {
        Sid      = "ReadWriteRawObjects"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.raw.arn}/*"
      }
    ]
  })
}
