## Machine Learning for Streaming

* Scenario
* Creating the role 
* Create a Lambda function, test it
* Create a Kinesis stream
* Connect the function to the stream
* Send the records 

Links


## Code snippets
Run the python script with live darwin kinesis records before building an image for containerization
bash
cd to this folder where the python scripts are
create a virtual environment
$ python -m venv venv
Activate virctual environment
$ source venv/Scripts/activate
Install libraries and dependencies
$ pip install boto3 sklearn joblib xmltodict pandas numpy boto3 xgboost pyarrow
$ python darwin_kinesis_producer.py
$ python kinesis_lambda_function.py
### Sending data


# Build the image
docker build -t arrival-delay-predictor .

# Tag for ECR
docker tag arrival-delay-predictor:latest <account_id>.dkr.ecr.<region>.amazonaws.com/arrival-delay-predictor:latest

# Push to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/arrival-delay-predictor:latest

🔗 Deploy to Lambda

In Lambda console → “Create function” → “Container image”.

Choose your ECR repo + tag.

Deploy 🎉.

Decoding base64

```python
base64.b64decode(data_encoded).decode('utf-8')
```

Record example

```xml
<Pport xmlns="http://www.thalesgroup.com/rtti/PushPort/v16" xmlns:ns2="http://www.thalesgroup.com/rtti/PushPort/Schedules/v3" xmlns:ns3="http://www.thalesgroup.com/rtti/PushPort/Schedules/v2" xmlns:ns4="http://www.thalesgroup.com/rtti/PushPort/Formations/v2" xmlns:ns5="http://www.thalesgroup.com/rtti/PushPort/Forecasts/v3" xmlns:ns6="http://www.thalesgroup.com/rtti/PushPort/Formations/v1" xmlns:ns7="http://www.thalesgroup.com/rtti/PushPort/StationMessages/v1" xmlns:ns8="http://www.thalesgroup.com/rtti/PushPort/TrainAlerts/v1" xmlns:ns9="http://www.thalesgroup.com/rtti/PushPort/TrainOrder/v1" xmlns:ns10="http://www.thalesgroup.com/rtti/PushPort/TDData/v1" xmlns:ns11="http://www.thalesgroup.com/rtti/PushPort/Alarms/v1" xmlns:ns12="http://thalesgroup.com/RTTI/PushPortStatus/root_1" ts="2025-08-18T09:48:46.4268177+01:00" version="16.0">
<uR updateOrigin="TD">
<TS rid="202508188967985" uid="Y67985" ssd="2025-08-18">
<ns5:Location tpl="DRUMRY" wta="09:45:30" wtd="09:46" pta="09:46" ptd="09:46">
<ns5:arr at="09:46" atClass="Automatic" src="TD"/>
<ns5:dep at="09:48" atClass="Automatic" src="TD"/>
<ns5:plat platsrc="A" conf="true">2</ns5:plat>
</ns5:Location>
<ns5:Location tpl="SINGER" wta="09:48" wtd="09:48:30" pta="09:48" ptd="09:48">
<ns5:arr et="09:50" src="Darwin"/>
<ns5:dep et="09:50" src="Darwin"/>
<ns5:plat platsrc="A" conf="true">2</ns5:plat>
</ns5:Location>
<ns5:Location tpl="DALMUIR" wta="09:51" pta="09:51">
<ns5:arr et="09:52" src="Darwin"/>
<ns5:plat platsrc="A" conf="true">1</ns5:plat>
</ns5:Location>
</TS>
</uR>
</Pport>
```


```

### Test event


```json
{
    "Records": [
        {
            "kinesis": {
                "kinesisSchemaVersion": "1.0",
                "partitionKey": "1",
                "sequenceNumber": "49630081666084879290581185630324770398608704880802529282",
                "data": "ewogICAgICAgICJyaWRlIjogewogICAgICAgICAgICAiUFVMb2NhdGlvbklEIjogMTMwLAogICAgICAgICAgICAiRE9Mb2NhdGlvbklEIjogMjA1LAogICAgICAgICAgICAidHJpcF9kaXN0YW5jZSI6IDMuNjYKICAgICAgICB9LCAKICAgICAgICAicmlkZV9pZCI6IDI1NgogICAgfQ==",
                "approximateArrivalTimestamp": 1654161514.132
            },
            "eventSource": "aws:kinesis",
            "eventVersion": "1.0",
            "eventID": "shardId-000000000000:49630081666084879290581185630324770398608704880802529282",
            "eventName": "aws:kinesis:record",
            "invokeIdentityArn": "arn:aws:iam::XXXXXXXXX:role/lambda-kinesis-role",
            "awsRegion": "eu-west-1",
            "eventSourceARN": "arn:aws:kinesis:eu-west-1:XXXXXXXXX:stream/ride_events"
        }
    ]
}
```

### Reading from the stream

```bash
KINESIS_STREAM_OUTPUT='arrival_delay_predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR)

echo ${RESULT} | jq -r '.Records[0].Data' | base64 --decode
``` 


### Running the test

```bash
export PREDICTIONS_STREAM_NAME="ride_predictions"
export RUN_ID="e1efc53e9bd149078b0c12aeaa6365df"
export TEST_RUN="True"

python test.py
```

### Putting everything to Docker

```bash
docker build -t stream-model-duration:v1 .

docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="e1efc53e9bd149078b0c12aeaa6365df" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="eu-west-1" \
    stream-model-duration:v1
```

URL for testing:

* http://localhost:8080/2015-03-31/functions/function/invocations



### Configuring AWS CLI to run in Docker

To use AWS CLI, you may need to set the env variables:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="e1efc53e9bd149078b0c12aeaa6365df" \
    -e TEST_RUN="True" \
    -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
    -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}" \
    stream-model-duration:v1
```

Alternatively, you can mount the `.aws` folder with your credentials to the `.aws` folder in the container:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="e1efc53e9bd149078b0c12aeaa6365df" \
    -e TEST_RUN="True" \
    -v c:/Users/alexe/.aws:/root/.aws \
    stream-model-duration:v1
```

### Publishing Docker images

Creating an ECR repo

```bash
aws ecr create-repository --repository-name duration-model
```

Logging in

```bash
$(aws ecr get-login --no-include-email)
```

Pushing 

```bash
REMOTE_URI="387546586013.dkr.ecr.eu-west-1.amazonaws.com/duration-model"
REMOTE_TAG="v1"
REMOTE_IMAGE=${REMOTE_URI}:${REMOTE_TAG}

LOCAL_IMAGE="stream-model-duration:v1"
docker tag ${LOCAL_IMAGE} ${REMOTE_IMAGE}
docker push ${REMOTE_IMAGE}
```
