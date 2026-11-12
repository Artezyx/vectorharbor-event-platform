# SkyRelay — AWS Serverless Event Processing

An independent Python 3.13 AWS SAM project combining API Gateway, Cognito authentication, Lambda, DynamoDB, SNS and SQS with a dead-letter queue.

## Architecture
Authenticated REST POST /events -> Lambda -> DynamoDB idempotency check -> SNS -> SQS -> worker Lambda -> DynamoDB delivery ledger.

## Test
python -m pip install -r requirements-dev.txt
python -m pytest -q

## Deploy
Install SAM CLI and AWS CLI; configure your AWS credentials and an existing Cognito user pool.
sam validate --template-file template.yaml
sam build
sam deploy --guided
Supply the CognitoUserPoolArn when prompted. AWS resource creation may incur charges.

## Engineering limitations
DynamoDB write followed by SNS publish is not atomic: a publisher outage can strand an event. Production should use an outbox or DynamoDB Streams. The worker is at-least-once, with a conditional-write delivery ledger; do not claim exactly-once external effects. The project has not been deployed to AWS, and no AWS integration or performance test is claimed.
