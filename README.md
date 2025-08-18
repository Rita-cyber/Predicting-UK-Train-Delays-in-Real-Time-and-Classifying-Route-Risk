# Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk


# Prerequisite

git clone https://github.com/openraildata/stomp-client-python.git
cd stomp-client-python

✅ In your terminal session, run:
export DARWIN_USERNAME='your_darwin_username'
export DARWIN_PASSWORD='your_darwin_password'
export KINESIS_STREAM_NAME='your_kinesis_stream_name'

Replace the values with your actual credentials and stream name.

✅ These variables will be available only in that terminal session.

If on Windows (Not WSL)
You can also install AWS CLI from the official Windows installer(https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

# Create a virtual environment with Python 3.8 or 3.9:
python3.9 -m venv darwin-env
source darwin-env/bin/activate
Then install PyXB:

bash
pip install pyxb

. aws configure
You’ll be prompted for:

AWS Access Key ID

AWS Secret Access Key

Default region

Output format (e.g., json)

Steps to Set It Up in AWS:
Go to the AWS Console
→ Kinesis Data Streams

Click "Create data stream"

Give it a name (e.g., darwin-rail-events) — this must match KINESIS_STREAM_NAME.

Choose:

Number of shards (start with 1 if testing)

Other options as needed

Click "Create data stream"

--Run locally first before on AWS

## Package into a Docker Container & Run on AWS Fargate or ECS
This is more scalable and serverless.

Containerize your script with dependencies.

Push to ECR.

Run in AWS Fargate.

<img width="711" height="241" alt="image" src="https://github.com/user-attachments/assets/cf41968a-bf96-4a4f-9b43-24135a115e4e" />


<img width="722" height="307" alt="image" src="https://github.com/user-attachments/assets/a36357f6-5e6b-4678-a4cf-7b1405fd5c90" />


## lambda Code

This script:

Parses incoming compressed XML messages.

Extracts features.

Runs a prediction using a model loaded from MLflow.

Sends the result to an AWS Kinesis stream.


<img width="718" height="357" alt="image" src="https://github.com/user-attachments/assets/fed3fc76-b7a6-44d6-8a4d-d0388c6f56e8" />




<img width="722" height="383" alt="image" src="https://github.com/user-attachments/assets/829c5df7-3722-4cec-9b7a-8900d44f0748" />



<img width="614" height="268" alt="image" src="https://github.com/user-attachments/assets/2d05562f-54c0-4bec-bc90-736dc28b2ff2" />




<img width="932" height="385" alt="image" src="https://github.com/user-attachments/assets/82112785-bf0d-4396-b4d9-eb56b1d504d2" />





<img width="921" height="311" alt="image" src="https://github.com/user-attachments/assets/48614245-b9a2-4de9-bd17-34ace3afe916" />


<img width="806" height="415" alt="image" src="https://github.com/user-attachments/assets/85ab3a9f-fac1-43e2-89f5-47fc8e64ac3d" />

## Spark Optimization
- Reduced execution time from 1hour to 28mimutes by optimizing query and dropping unwanted columns before shuffle

  <img width="736" height="346" alt="image" src="https://github.com/user-attachments/assets/5db6be96-f3ed-40f6-aa38-7484ed6bc0c5" />



## Evidently_Data Qulity Monitoring

<img width="915" height="437" alt="image" src="https://github.com/user-attachments/assets/360855d9-b7cd-40db-badf-68801118ac74" />

<img width="732" height="375" alt="image" src="https://github.com/user-attachments/assets/2139a47e-0d3c-411c-be14-7eb2c3618a2d" />


<img width="732" height="275" alt="image" src="https://github.com/user-attachments/assets/2f6cc7be-52c7-4df0-ad26-1f76e0111f9f" />


<img width="647" height="349" alt="image" src="https://github.com/user-attachments/assets/015cfd41-1883-4eae-a011-3ea21eab579f" />

<img width="620" height="231" alt="image" src="https://github.com/user-attachments/assets/6a534783-2d86-46c1-8067-98c8c3fac0c1" />

<img width="620" height="229" alt="image" src="https://github.com/user-attachments/assets/5b5b1fa9-fd28-4bc5-8b95-684712d9c302" />












