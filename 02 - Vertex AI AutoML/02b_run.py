"""
Notebook 02b (most of) in a script.

Highlights:
- toDo
"""

import os 
import json
import requests
import numpy as np
from datetime import datetime

from google.cloud import aiplatform, bigquery
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from google.cloud.secretmanager import SecretManagerServiceClient


### --- Set Up
# params
PROJECT_ID = os.popen('gcloud config get-value project').read()[:-1]
smc = SecretManagerServiceClient()
REGION = smc.access_secret_version(
    request={"name": f"projects/{PROJECT_ID}/secrets/PARAM_REGION/versions/latest"}
).payload.data.decode("UTF-8")
DATANAME = 'fraud'
NOTEBOOK = '02b'
DEPLOY_COMPUTE = 'n1-standard-2'

# model params
MODEL_VARS = {
    'target': ['class'],      
    'omit': ['transaction_id', 'splits']
}
TIMESTAMP = datetime.now().strftime("%Y%m%d%H%M%S")
DIR = f"temp/{NOTEBOOK}"

# environment
os.system(f"rm -rf {DIR}")
os.system(f"mkdir -p {DIR}")

# set clients
aiplatform.init(project=PROJECT_ID, location=REGION)
bq = bigquery.Client()

### create dataset in ai platform
dataset = aiplatform.TabularDataset.create(
    display_name = f'{NOTEBOOK}_{DATANAME}_{TIMESTAMP}', 
    bq_source = f'bq://{PROJECT_ID}.{DATANAME}.{DATANAME}_prepped',
    labels = {'notebook':f'{NOTEBOOK}'}
)

### Build AutoML model
# get features list
features_list = set(dataset.column_names) - set(MODEL_VARS['target'] + MODEL_VARS['omit'])
column_specs = dict.fromkeys(features_list, 'auto')

# set training job
tabular_classification_job = aiplatform.AutoMLTabularTrainingJob(
    display_name = f'{NOTEBOOK}_{DATANAME}_{TIMESTAMP}',
    optimization_prediction_type = 'classification',
    optimization_objective = 'maximize-au-prc',
    column_specs = column_specs,
    labels = {'notebook':f'{NOTEBOOK}', 'sal_label': 'dummy'}
)
# # run training 
# model = tabular_classification_job.run(
#     dataset = dataset,
#     target_column = MODEL_VARS['target'],
#     predefined_split_column_name = 'splits',
#     #    training_fraction_split = 0.8,
#     #    validation_fraction_split = 0.1,
#     #    test_fraction_split = 0.1,
#     budget_milli_node_hours = 1000,
#     model_display_name = f'{NOTEBOOK}_{DATANAME}_{TIMESTAMP}',
#     disable_early_stopping = False,
#     model_labels = {'notebook':f'{NOTEBOOK}'}
# )

### To avoid extra costs, we here pick any trained model
models_list = aiplatform.Model.list()
model = models_list[0]
print(f"Taken model {model.display_name}: {model.name}")

### See evaluations
evaluations_list = model.list_model_evaluations()
evaluation = evaluations[0]
for metric, value in evaluation.metrics.items():
    if metric == 'confidenceMetrics':
        continue
    print(f"{metric},{value}")
    
### See evaluation slices
model_client = aiplatform.gapic.ModelServiceClient(
    client_options={"api_endpoint": f'{REGION}-aiplatform.googleapis.com'})

slices_list = model_client.list_model_evaluation_slices(
    # str like 'projects/PROJECT-ID/locations/REGION/models/MODEL-ID/evaluations/EVAL-ID'
    parent=model_client.model_evaluation_path(
        project=PROJECT_ID, location=REGION, model=model.name, evaluation=evaluation.name
    )
)
for me_slice in response:
    # print("model_evaluation_slice:", me_slice)
    print('Label = ', me_slice.slice_.value, 'has auPrc = ', me_slice.metrics['auPrc'])
    
    
    