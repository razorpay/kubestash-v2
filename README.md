# Kubestash-V2
Sync key-value pair from DDB Credstash table to Kubernetes secrets.

Accepted format in Key-Value table:
- namespace/secret-name/KEY
- There is no restriction on value for the above KEY.

**Example:**

DynamoDB table which has below key-value pair:

`test/mysecret/TEST_KEY`: `$ecreT`

will be synced in k8s as `test` namespace in `mysecret` Opaque secret with `TEST_KEY` as key and value as `$ecreT` in base64 encoded format.

> [!IMPORTANT]
> Before syncing the secrets:
> 1. TEST_KEY will be converted to CAPS if in small.
> 2. `.` & `-` will be replaced to `_`.  


### Before We Start
We've following requirments:
- [Credstash](https://github.com/fugue/credstash) Table in AWS
- OIDC enabled Kubernetes Cluster with version 1.22 and above with kube-state-metrics.
> Note: It may work with lower version of k8s as well.
- [DDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html#Streams.Enabling) enabled for DynamoDB table with `New Image` option.
- Service Account `kubestash-v2` with following:
  * IAM policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": "kms:Decrypt",
            "Resource": "arn:aws:kms:<AWS_Region_Code>:<AWS_Account_ID>:key/<KMS_Key_ID>"
        },
        {
            "Sid": "",
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:ListStreams",
                "dynamodb:GetShardIterator",
                "dynamodb:GetRecords",
                "dynamodb:GetItem",
                "dynamodb:DescribeTable",
                "dynamodb:DescribeStream",
                "dynamodb:BatchGetItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:<AWS_Region_Code>:<AWS_Account_ID>:table/<DDB_TABLE_NAME>",
                "arn:aws:dynamodb:<AWS_Region_Code>:<AWS_Account_ID>:table/<DDB_TABLE_NAME>/stream/*"
            ]
        }
    ]
}
```
-  * Trust Relationship
```
{
    "Sid": "",
    "Effect": "Allow",
    "Principal": {
        "Federated": "arn:aws:iam::<AWS_Account_ID>:oidc-provider/oidc.eks.ap-south-1.amazonaws.com/id/<OIDC_UNIQUE_ID>"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
        "StringEquals": {
            "oidc.eks.<AWS_Region_Code>.amazonaws.com/id/<OIDC_UNIQUE_ID>:aud": "sts.amazonaws.com",
            "oidc.eks.<AWS_Region_Code>.amazonaws.com/id/<OIDC_UNIQUE_ID>:sub": [
                "system:serviceaccount:kubestash-v2:kubestash-v2"
            ]
        }
    }
}
```

> [!TIP] 
> Please replace the `AWS_Region_Code`, `AWS_Account_ID`, `KMS_Key_ID`, `DDB_TABLE_NAME`, `OIDC_UNIQUE_ID` 
> based on your EKS configuration. 

- Prometheus and Grafana Monitoring for visualisation and alerts.
### Key Featuers
  1. Listen the secrets changes in table in real time.
  1. Able to log the steps it’s doing
  1. Debug mode for more verbose logging
  1. Emit metrics for the sync/fail status
  1. Configuration Visibility
  1. Efficient k8s api calls
  1. Detect failures and restart itself automatically
  1. Feature rich dashboard to monitor and analysis
  1. Dry Run mode to observe the behaviour of application
  1. Starts the sync process as soon as deployment comes up and thereafter based on DDB events or cron timeperiod.
  1. Cancel and restart itself if stuck in data fetch and sync step more than given time.

### Enviroments Variables

### Metrics Description

### Deployment Nuances
- Create namespace `kubestash-v2` and Opaque secret `kubestash-v2` with `FLASK_API_KEY` val before deployment of helm-chart.
> [!NOTE]
> FLASK_API_KEY will be used to trigger manual sync operation as well as by our cron that is running along with our main container.
- Please update parametes in `values.yaml` based on your infra.  

## Feature Request/Issue
Please follow the template attached to rasie an issue OR mail us at `devops@razorpay.com`

## TODO
1. Remove hardcoded namespace requirment `kubestash-v2`
2. Add unit tests and coverage.
3. Migrate to [logger](https://docs.python.org/3/library/logging.html#) instead of print statements.

## Thanks
We've taken inspiration from following repos to implement some of our featuers:
- [func_timeout](https://github.com/ikamensh/func_timeout/tree/master)
- [Monitoring DDB with streams](https://www.tecracer.com/blog/2022/05/getting-a-near-real-time-view-of-a-dynamodb-stream-with-python.html)