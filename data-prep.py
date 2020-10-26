import boto3
import time
import os
import sys
import wget

start = time.time()

source = sys.argv[1]
bucket = sys.argv[2]
prefix = sys.argv[3]

s3 = boto3.resource('s3')

def download(url):
    filename = url.split("/")[-1]
    if not os.path.exists(filename):
        wget.download(url, filename)

def upload_to_s3(prefix, channel, file):
    data = open(file, "rb")
    key = '{}/{}/{}'.format(prefix, channel, file)
    s3.Bucket(bucket).put_object(Key=key, Body=data)

# This examples downloads recordIO files that have already be split into train/Test
# For the process of creating these files see the "im2rec.py" as part of mxnet
# see: https://gluon-cv.mxnet.io/build/examples_datasets/recordio.html

print ("Downloadng Training Data")
download(os.path.join(source, 'caltech-256-60-train.rec'))
upload_to_s3(prefix, 'train', 'caltech-256-60-train.rec')
print ("Finished Downloadng Training Data")

print ("Downloadng Testing Data")
download(os.path.join(source, 'caltech-256-60-val.rec'))
upload_to_s3(prefix, 'validation', 'caltech-256-60-val.rec')
print ("Finished Downloadng Testing Data")

end = time.time()
print(end - start)
