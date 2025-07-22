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






