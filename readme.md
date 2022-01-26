# TwitFix

[`robinuniverse`](https://github.com/robinuniverse/TwitFix)'s wonderful TwitFix tool ported to run as an AWS Lambda function, triggered by an AWS API Gateway endpoint.

Most of the extra clever stuff doesn't work because I just wanted to make a proof-of-concept first. For instance, doesn't support the MP4 links.

Also @TODO is reintroducing the vnf cache in the form of Elasticache or DynamoDB. Additionally capturing all the AWS infra as a CloudFormation template.
