provider "aws" {
  region = "us-east-1"  # The current region, dont change it
}

terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket         = "danoch-terraform-state"
    key            = "incident-management/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "danoch-terraform-locks"  # Optional for state locking, check notes 
  }
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "danoch-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

resource "aws_instance" "incident_test_instance" {
  ami           = "ami-04681163a08179f28"  # Amazon Linux 2 AMI (x86_64)
  instance_type = "t2.micro"
  key_name      = "NewDanochKeyPair"  # Use the key pair you just created | new keypair updated
  security_groups = ["default"]

  tags = {
    Name = "Incident-Test-Instance"
  }
}


# Creating an SNS topic for incident notifications
resource "aws_sns_topic" "incident_notifications" {
  name = "incident-notifications"
}

# Subscribe an email to receive notifications
resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.incident_notifications.arn
  protocol  = "email"
  endpoint  = "daniel.martinez.vfi@gmail.com" 
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "HighCPUAlarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80  # it could be less than 80%
  alarm_description   = "Triggers when CPU usage exceeds 80% for 5 minutes"

  dimensions = {
    InstanceId = "<i-0837de3f357c2a0c4>"
  }

  actions_enabled = true
  alarm_actions   = [aws_sns_topic.incident_notifications.arn]
}



resource "aws_lambda_function" "incident_handler" {
  function_name = "incident-response-lambda"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"

  filename         = "lambda_function.zip"  # We will create this file for lambda actions
  source_code_hash = filebase64sha256("lambda_function.zip")

  environment {
    variables = {
      LOG_LEVEL = "INFO"
      SNS_TOPIC_ARN = aws_sns_topic.incident_notifications.arn
    }
  }
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec" {
  name = "incident_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy to Allow Lambda to Restart EC2 Instances
resource "aws_iam_policy" "lambda_ec2_policy" {
  name = "LambdaEC2RestartPolicy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:DescribeInstances",
          "ec2:RebootInstances"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_ec2_policy.arn
}


