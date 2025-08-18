# 3. Orchestration and ML Pipelines

The Apache Airflow is used as an orchestrator tool to trigger aws glue jobs

The Apache Airflow is run on-prem to manage cost,apache airflow doesnt excute the task it only triggers the jobs in aws glue.

Aws Glue executes the task for scalability and production-ready.

AWS Glue is used because it has the flexibilty to handle large datasets due to its pyspark runtime.

I noticed that the data stream is quite large even for few minutes of streaming as the Darwin stream of rail data is for the whole of UK which is quite large.

## 3.1 Apache Airflow setup environment
bash
$ docker-compose up --build(this builds the dockerfile)

The Apache Airflow picks data from the processed folder stored in S3 bucket and runs task till registering of model.

## 3.3 AWS Glue Setup

- Configure the required IAM Role for Glue to access S3 bucket.

<img width="732" height="275" alt="image" src="https://github.com/user-attachments/assets/2f6cc7be-52c7-4df0-ad26-1f76e0111f9f" />

- Create jobs for each of the python scripts and upload each as python shell scripts only transformed-spark.py should be uploaded to the spark script since we used apapche spark for that process.

<img width="620" height="231" alt="image" src="https://github.com/user-attachments/assets/6a534783-2d86-46c1-8067-98c8c3fac0c1" />

<img width="620" height="229" alt="image" src="https://github.com/user-attachments/assets/5b5b1fa9-fd28-4bc5-8b95-684712d9c302" />

- Set job parameters for each of the jobs as seen below,the job parameters are the function arguments or parameters required in the function .

<img width="647" height="349" alt="image" src="https://github.com/user-attachments/assets/015cfd41-1883-4eae-a011-3ea21eab579f" />


### Step 3: Orchestrating the Workflow

* Airflow used to orchestrate the steps in the National_rail_etl_ml_dags.py

### Step 4: Parametrizing the Workflow

* Schedule the workflow to run monthly

### Step 5: Backfilling

* Airflow is able to run the workflow for some of the past months,however this project is a real-time streaming prediction.








