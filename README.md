# Kubestash-V2
We're using the [Kubestash](https://github.com/razorpay/kubestash) to sync our secrets but earlier has **problems related to logging, metrics and no crashloop recovery**.
We've faced lot of incidents due to mismatch of secrets when application got crashed and no proper alerts were present to notifiy them.
Keeping above in place, we've introduced `Kubestash-V2` to tackle those problems.  


--------------------------------------------------------------------------------------
Sync key-value pair from AWS DynamoDB Credstash table to Kubernetes EKS secrets.

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

The sync will happen one way i.e from DDB table to K8s secret. Manually created secrets will not be touched and remain as it is if they are not present in DDB table.
DDB table will be taken as source of truth for sync operation.

## Before We Start
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

## Key Featuers
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
  1. Manually created secrets will be untouched if they are not present in DynamoDB table else it will be replaced with table value.
  1. Will add annotation in secret for time when it is updated.
  1. There will be rate limit on flask-server `/syncnow` api call as well. [1 request per 10 min] However this is configurable in code.
  1. 1 replica for application will be running and will restart itself in [Recreate](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#recreate-deployment) mode.   


## Enviroments Variables
|               Parameter                     |                          Description                         |                       Default                     |
| ------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| `env`                                       | Environment in which application is running. Ex: stage/prod  | `stage`                                           |
| `cluster_name`                              | Name of EKS cluster                                          | NULL                                              |
| `ddb_table`                                 | Dynamo DB Table Name                                         | NULL                                              |
| `table_region`                              | AWS Region for DynamoDB Table                                | `ap-south-1`                                      |
| `stream_arn`                                | ARN for DynamoDB Stream                                      | NULL                                              |
| `namespace_exclude_filter`                  | Namespace seperated by `\|` excluded from syncing by app     | `kube-system\|kubestash-v2\|kubestash`            |
| `wait_time`                                 | Wait seconds after app receive the changes in DDB table and start sync operation | `120`                         |
| `cron_hours`                                | Hours at which cron will trigger manual sync                 | `3`                                               |
| `verbose`                                   | Default is false. Set it "true" for debugging purpose only.  | `""`                                              |
| `dry_run`                                   | Update/Create APIs for secret won't actully updating the secret. | `true`                                        |
| `http_timeout`                              | Timeout for Kubernetes APIs call                             | `15`                                              |
| `prometheus_multiproc_dir`                  | Directroy/file for metrics capturing in multiprocessing      | `./prom`                                          |
| `credstash_sync_timeout_secs`               | Timeout seconds after which sync operation got cancelled and app is restarted.    | `300`                        |
## Metrics Description

We are exposing below prometheus metrics in order to have better monitoring in our application. Along with kubernetes metrics, we can create reliable alerts and monitoring system for ourselves. Please refer `monitoring` directory for dashboards.
|                Metrics                      |                          Description                         |
| ------------------------------------------- | ------------------------------------------------------------ |
| `kubestash_v2_settings`                     | Settings currently used by kubestash                         |
| `kubestash_key_synced_failed_status`        | Gauge with failed keys. 1 for failed. 0 for normal           |
| `kubestash_table_fetch_status`              | Gauge with stucked table status. 1 or failed. 0 for normal   |
| `kubestash_429_requests_count`              | Counter for bad requests                                     |
| `kubestash_404_request_count`               | Counter for non found requests                               |
| `kubestash_400_request_count`               | Counter for malformed requests                               |
| `kubestash_500_request_count`               | Counter for internal server error                            |
| `kubestash_200_request_count`               | Counter for valid request                                    |
| `kubestash_ddb_fetch_seconds`               | Time spent fetching DDB data                                 |

## Deployment Nuances
- Create namespace `kubestash-v2` and Opaque secret `kubestash-v2` with `FLASK_API_KEY` val before deployment of helm-chart.
> [!NOTE]
> FLASK_API_KEY will be used to trigger manual sync operation as well as by our cron that is running along with our main container.
- [Build](https://docs.docker.com/engine/reference/commandline/build/) MAIN docker image using `src/Dockerfile` and push it to your registry. We are not building/pushing the image as of now.
- Build SIDECAR docker image using `cron/Dockerfile` and push it to your registry. We are not building/pushing the image as of now.
- Please update parametes in `deployment/helm-charts/values.yaml` based on your infra and above docker builds. 

## Feature Request/Issue
Please follow the template attached to rasie an issue OR mail us at `devops+kubestash@razorpay.com`

## TODO
1. Remove hardcoded namespace requirment `kubestash-v2`
2. Add unit tests and coverage.
3. Migrate to [logger](https://docs.python.org/3/library/logging.html#) instead of print statements.

## Thanks
We've taken inspiration from following repos to implement some of our featuers:
- [func_timeout](https://github.com/ikamensh/func_timeout/tree/master)
- [Monitoring DDB with streams](https://www.tecracer.com/blog/2022/05/getting-a-near-real-time-view-of-a-dynamodb-stream-with-python.html)