import boto3
import time
from time import gmtime, strftime
import sys
import json

# Different algorithms have different registry and account parameters
# see: https://github.com/aws/sagemaker-python-sdk/blob/master/src/sagemaker/amazon/amazon_estimator.py#L272
def get_image_uri(region_name):
    """Return image classificaiton algorithm image URI for the given AWS region"""
    account_id = {
        "us-east-1": "811284229777",
        "us-east-2": "825641698319",
        "us-west-2": "433757028032",
        "eu-west-1": "685385470294",
        "eu-central-1": "813361260812",
        "ap-northeast-1": "501404015308",
        "ap-northeast-2": "306986355934",
        "ap-southeast-2": "544295431143",
        "us-gov-west-1": "226302683700"
    }[region_name]
    return '{}.dkr.ecr.{}.amazonaws.com/image-classification:latest'.format(account_id, region_name)

start = time.time()

region_name = sys.argv[1]
execution_role = sys.argv[2]
autoscaling_role = sys.argv[3]
bucket = sys.argv[4]
prefix = sys.argv[5]
stack_name = sys.argv[6]
commit_id = sys.argv[7]
commit_id = commit_id[0:7]

training_image = get_image_uri(region_name)
timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())

print ("ChangYoon First Python")
print ("Setting Algorithm Settings")
# The algorithm supports multiple network depth (number of layers). They are 18, 34, 50, 101, 152 and 200
# For this training, we will use 18 layers
num_layers = "18"
# we need to specify the input image shape for the training data
image_shape = "3,224,224"
# we also need to specify the number of training samples in the training set
# for caltech it is 15420
num_training_samples = "15420"
# specify the number of output classes
num_classes = "257"
# batch size for training
mini_batch_size =  "64"
# number of epochs
epochs = "1"
# learning rate
learning_rate = "0.01"

# create unique job name
job_name = stack_name + "-" + commit_id + "-" + timestamp
output_path = 's3://{}/{}/output'.format(bucket, prefix)
training_params = \
{
    # specify the training docker image
    "AlgorithmSpecification": {
        "TrainingImage": training_image,
        "TrainingInputMode": "File"
    },
    "RoleArn": execution_role,
    "OutputDataConfig": {
        "S3OutputPath": output_path
    },
    "ResourceConfig": {
        "InstanceCount": 1,
        "InstanceType": "ml.p2.xlarge",
        "VolumeSizeInGB": 50
    },
    "TrainingJobName": job_name,
    "HyperParameters": {
        "image_shape": image_shape,
        "num_layers": str(num_layers),
        "num_training_samples": str(num_training_samples),
        "num_classes": str(num_classes),
        "mini_batch_size": str(mini_batch_size),
        "epochs": str(epochs),
        "learning_rate": str(learning_rate)
    },
    "StoppingCondition": {
        "MaxRuntimeInSeconds": 360000
    },
#Training data should be inside a subdirectory called "train"
#Validation data should be inside a subdirectory called "validation"
#The algorithm currently only supports fullyreplicated model (where data is copied onto each machine)
    "InputDataConfig": [
        {
            "ChannelName": "train",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": 's3://{}/{}/train/'.format(bucket, prefix),
                    "S3DataDistributionType": "FullyReplicated"
                }
            },
            "ContentType": "application/x-recordio",
            "CompressionType": "None"
        },
        {
            "ChannelName": "validation",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": 's3://{}/{}/validation/'.format(bucket, prefix),
                    "S3DataDistributionType": "FullyReplicated"
                }
            },
            "ContentType": "application/x-recordio",
            "CompressionType": "None"
        }
    ]
}
print('Training job name: {}'.format(job_name))
print('\nInput Data Location: {}'.format(training_params['InputDataConfig'][0]['DataSource']['S3DataSource']))

# create the Amazon SageMaker training job
sagemaker = boto3.client(service_name='sagemaker')
sagemaker.create_training_job(**training_params)

# confirm that the training job has started
status = sagemaker.describe_training_job(TrainingJobName=job_name)['TrainingJobStatus']
print('Training job current status: {}'.format(status))

try:
    # wait for the job to finish and report the ending status
    sagemaker.get_waiter('training_job_completed_or_stopped').wait(TrainingJobName=job_name)
    training_info = sagemaker.describe_training_job(TrainingJobName=job_name)
    status = training_info['TrainingJobStatus']
    print("Training job ended with status: " + status)
except:
    print('Training failed to start')
     # if exception is raised, that means it has failed
    message = sagemaker.describe_training_job(TrainingJobName=job_name)['FailureReason']
    print('Training failed with the following error: {}'.format(message))


# creating configuration files so we can pass parameters to our sagemaker endpoint cloudformation

config_data_qa = {
  "Parameters":
    {
        "Environment": "qa",
        "ParentStackName": stack_name,
        "JobName": job_name,
        "ModelOutputPath": output_path,
        "SageMakerRole": execution_role,
        "SageMakerImage": training_image
    }
}

config_data_prod = {
  "Parameters":
    {
        "Environment": "prod",
        "ParentStackName": stack_name,
        "JobName": job_name,
        "ModelOutputPath": output_path,
        "SageMakerRole": execution_role,
        "SageMakerImage": training_image,
        "AutoScalingRole": autoscaling_role,
    }
}


json_config_data_qa = json.dumps(config_data_qa)
json_config_data_prod = json.dumps(config_data_prod)

f = open( './CloudFormation/configuration_qa.json', 'w' )
f.write(json_config_data_qa)
f.close()

f = open( './CloudFormation/configuration_prod.json', 'w' )
f.write(json_config_data_prod)
f.close()

end = time.time()
print(end - start)
