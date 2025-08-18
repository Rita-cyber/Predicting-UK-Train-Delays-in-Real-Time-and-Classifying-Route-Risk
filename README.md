# Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk


## Problem Statement
Problem Statement

Train delays are a persistent challenge within the UK railway network, affecting passengers, operators, and the wider economy. Current real-time information systems primarily focus on reporting delays after they occur, leaving passengers and operators with limited ability to anticipate disruptions and plan accordingly.

With the growing availability of real-time railway data (e.g., Darwin Push Port feeds from National Rail) and advanced machine learning methods, there is an opportunity to predict delays before they happen. By leveraging historical and live train movement data, operators can provide early warnings to passengers, optimize resource allocation, and reduce the negative impact of disruptions.

Key challenges include:

High variability in train arrival times due to multiple external factors (weather, congestion, incidents, etc.).

The need to process large volumes of streaming XML data from Darwin feeds in real time.

Transforming raw, nested railway data into meaningful features for machine learning.

Ensuring scalability, reliability, and integration with operational systems.

Business Requirements
1. Real-Time Delay Prediction

The system must predict train arrival delays (in minutes) for UK National Rail services in near real time.

Predictions should be updated continuously as new real-time feed data arrives.

2. Data Ingestion and Processing

Ingest real-time train movement and schedule data from the Darwin Push Port feed via AWS Kinesis.

Store both raw XML data and processed tabular data (CSV/Parquet) in AWS S3 for historical analysis.

Apply transformations (normalization, timestamp alignment, feature engineering) to prepare features for machine learning.

3. Machine Learning Model Lifecycle

Train and evaluate machine learning models (e.g., Random Forest, XGBoost, Linear Regression) on historical data.

Register the best-performing model in MLflow Model Registry with versioning and metadata.

Deploy the model for real-time inference within a Lambda function, integrated with the streaming pipeline.

4. Orchestration and Automation

Use Apache Airflow to orchestrate data workflows, including ETL, model training, evaluation, and deployment.

Use AWS Glue for large-scale batch transformations of historical data.

5. Monitoring and Governance

Track pipeline health, job failures, and data quality issues.

Monitor prediction accuracy drift using Evidently AI and visualize metrics in Grafana dashboards.

Ensure compliance with data governance and security standards.

6. End-User Impact

Provide train operators with dashboards or APIs to view predicted arrival times and potential delays.

Improve passenger experience by enabling better journey planning through more accurate, predictive information.

Support operational decision-making (e.g., staffing, resource allocation) during disruption scenarios.

✅ This positions the project as both a data engineering and machine learning in production (MLOps) use case, highlighting the technical and business impact.



# Deployment Architecture

<img width="599" height="385" alt="image" src="https://github.com/user-attachments/assets/e3ab64bf-b5e4-47f7-8347-f69a46de78b8" />


# Orchestration Architecture

<img width="729" height="404" alt="image" src="https://github.com/user-attachments/assets/f24b7da5-670d-45e0-97bf-fa7fbcd387dd" />


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












