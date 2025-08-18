# Monitoring of ML Models and Data Quality with Evidently and Grafana

## 1. Set up environment 

bash:
-mkdir monitoring ## create a folder called monitoring
-cd monitoring
-conda create -n pyrail python=3.11 ## note: evidently works well with python=3.11.pyrail is the name of the virtual environment,you can choose another name
-conda activate pyrail ## activate the virtual environment

## copy the dockercompose.yml and requirements.txt from this folder

bash
- pip install -r requirements.txt
- docker-compose up --build ## to build the container for the first time

## Copy the baseline-model.py and evidently-data-quality.py script,run each cell for and login respectively to evidently,Grafana an dadminer for data quality monitoring.


## How to access evidently,grafana,adminer
evidently:
bash
- evidently ui

Grafana: http://localhost:3000
Default username-admin
Default password-admin

Adminer:http://localhost:8080
username- based on what is configured on docker-compose postgres
password- based on what is configured on docker-compose postgres
