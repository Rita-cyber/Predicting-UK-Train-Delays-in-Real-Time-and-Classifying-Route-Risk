# Predicting-UK-Train-Delays-in-Real-Time


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









# Cloud Monitoring


<img width="932" height="385" alt="image" src="https://github.com/user-attachments/assets/82112785-bf0d-4396-b4d9-eb56b1d504d2" />





<img width="921" height="311" alt="image" src="https://github.com/user-attachments/assets/48614245-b9a2-4de9-bd17-34ace3afe916" />


<img width="806" height="415" alt="image" src="https://github.com/user-attachments/assets/85ab3a9f-fac1-43e2-89f5-47fc8e64ac3d" />

## Spark Optimization
- Reduced execution time from 1hour to 28mimutes by optimizing query and dropping unwanted columns before shuffle

  <img width="736" height="346" alt="image" src="https://github.com/user-attachments/assets/5db6be96-f3ed-40f6-aa38-7484ed6bc0c5" />



## Evidently_Data Quality Monitoring

<img width="915" height="437" alt="image" src="https://github.com/user-attachments/assets/360855d9-b7cd-40db-badf-68801118ac74" />

<img width="732" height="375" alt="image" src="https://github.com/user-attachments/assets/2139a47e-0d3c-411c-be14-7eb2c3618a2d" />


## Project Procedure
- Clone the repo
$ git clone https://github.com/Rita-cyber/Predicting-UK-Train-Delays-in-Real-Time-and-Classifying-Route-Risk.git

- Follow the instructions of the ReadMe of code/Containerization-Darwin-Producer Folder
- Follow the instructions on the ReadMe of code/orchestration Folder
- Follow the instructions on the ReadMe of code/Deployment Folder
- Follow the instructions on the ReadMe of code/Monitoring Folder.












