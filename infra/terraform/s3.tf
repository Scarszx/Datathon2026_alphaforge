# storage-dataset : bucket privé du jeu de données (lecture seule à l'exécution),
# et le front (bucket privé + CloudFront avec OAC, décision de l'équipe).

resource "aws_s3_bucket" "dataset" {
  bucket = local.dataset_bucket
}

resource "aws_s3_bucket_public_access_block" "dataset" {
  bucket = aws_s3_bucket.dataset.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dataset" {
  bucket = aws_s3_bucket.dataset.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- Front ---

resource "aws_s3_bucket" "front" {
  bucket = local.front_bucket
}

resource "aws_s3_bucket_public_access_block" "front" {
  bucket = aws_s3_bucket.front.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "front" {
  bucket = aws_s3_bucket.front.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Origin Access Control : CloudFront seul peut lire le bucket du front.
resource "aws_cloudfront_origin_access_control" "front" {
  name                              = "${var.name_prefix}-front-oac"
  description                       = "Accès CloudFront au bucket du front"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "front" {
  enabled             = true
  comment             = "AlphaForge front (SPA)"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.front.bucket_regional_domain_name
    origin_id                = "front"
    origin_access_control_id = aws_cloudfront_origin_access_control.front.id
  }

  default_cache_behavior {
    target_origin_id       = "front"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  }

  # SPA : les chemins inconnus servent index.html (routage côté front).
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}

resource "aws_s3_bucket_policy" "front" {
  bucket = aws_s3_bucket.front.id
  depends_on = [
    aws_s3_bucket_public_access_block.front,
  ]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.front.arn}/*"
        Condition = {
          ArnLike = {
            "AWS:SourceArn" = "arn:aws:cloudfront::${local.account_id}:distribution/${aws_cloudfront_distribution.front.id}"
          }
        }
      }
    ]
  })
}
