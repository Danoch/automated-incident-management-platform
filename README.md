Automated Incident Management Platform

A DevOps Project using AWS, Terraform, GitLab CI/CD, CloudWatch, and PM2

-- Overview

This project is a full-scale automated incident management system designed to:
- Detect failures automatically (CloudWatch Alarms).
- Trigger incident response via AWS Lambda & SNS.
- Restart failed EC2 instances automatically.
- Deploy full-stack applications (Lightweight App) using GitLab CI/CD.
- Monitor & Log incidents with Datadog.
- Ensure uptime with PM2 & Nginx.

-- Tech Stack

Category				Technologies Used
Cloud Provider				AWS (EC2, Lambda, CloudWatch, SNS, S3, IAM)
Infrastructure as Code (IaC)		Terraform
CI/CD					GitLab CI/CD
Application Backend			Node.js, Express.js, SQLite
Application Frontend			Next.js
Process Management			PM2
Monitoring & Logging			AWS CloudWatch Logs
Reverse Proxy				Nginx

-- Project Features

- AWS CloudWatch Alarms detect failures (high CPU usage, app crashes).
- AWS Lambda function automatically restarts EC2 instances on failures.
- GitLab CI/CD Pipeline automates deployments to AWS services & EC2.
- Full-stack app (Express.js Backend + Next.js Frontend) deployed via pipeline.
- Infrastructure managed using Terraform for repeatability.
- PM2 ensures app uptime and restarts services when they crash.

--️ Setup Instructions

1. Clone the Repository
	git clone https://github.com/your-username/your-repo.git
	cd your-repo

⃣2. Deploy Infrastructure (Terraform)
	terraform init
	terraform apply -auto-approve

3.Deploy & Run the Lightweight App
	cd lightweight-app
	npm install
	pm2 start src/index.js --name backend

4. Run Frontend
	cd ../lightweight-frontend
	npm install
	npm run build
	npm start

-- GitLab CI/CD Pipeline

The project includes a fully automated GitLab CI/CD pipeline for deployment:

Pipeline Stages
1. Test: Runs unit tests (if available).
2. Package: Packages Lambda functions.
3. Deploy to AWS Lambda: Uploads function updates.
4. Deploy Lightweight App (EC2): SCP + SSH Deployments.
5. Restart Services & Update Nginx.

Pipeline Configuration (.gitlab-ci.yml):

deploy_lightweight_app:
  stage: deploy_lightweight_app
  script:
    - echo "🚀 Deploying Lightweight Backend..."
    - scp -r src package.json package-lock.json .env database.sqlite $EC2_USER@$EC2_HOST:$LIGHTWEIGHT_BACKEND_DIR
    - ssh $EC2_USER@$EC2_HOST << 'EOF'
        cd $LIGHTWEIGHT_BACKEND_DIR
        npm install
        pm2 restart backend || pm2 start src/index.js --name backend
        pm2 save
      EOF
    - echo "🚀 Restarting Nginx..."
    - ssh $EC2_USER@$EC2_HOST "sudo systemctl restart nginx"
  only:
    - main

-- API Endpoints

Method	Endpoint	Description
GET	/api/users	Get all users
POST	/api/users	Add a new user
GET	/	Health check

Example: Add a new user

curl -X POST http://your-ip:4000/users -H "Content-Type: application/json" -d '{"name": "Daniel", "email": "daniel.martinez.vfi@gmail.com"}'

-- Future Improvements

- Implement Auto Scaling for EC2 instances.
- Add Database Migration to PostgreSQL (AWS RDS) for production readiness.
- Improve Monitoring & Alerting with Datadog dashboards.
- Add Canary Deployment for Frontend & Backend updates.

-- Conclusion

This project showcases a real-world DevOps implementation, combining AWS, Terraform, GitLab CI/CD, Node.js, Next.js, and PM2 to build a fully automated, resilient, and scalable incident response system.


-- Feel free to fork, contribute, and improve! 🚀

-- Commit and Push Changes
