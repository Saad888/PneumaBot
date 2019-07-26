"""
This module is dedicated to grabbing and posting the updated configurations
files to Amazon S3.

Create an instance of the S3BucketClient to operate

Probably should make this into a separate library eventually
"""

import asyncio
import aioboto3
import botocore
import os
import exceptions


class S3BucketClient:
    class HTTPError:
        """Decorator for catching failed HTTP requests and formatting them"""
        def catch(func):
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except botocore.exceptions.ClientError as e:
                    raise exceptions.S3RequestError('HTTP Error: {}, {}'.format(
                        e.response['Error']['Code'], 
                        e.response['Error']['Message']
                    ))
            return wrapper


    def __init__(self, AWSKEY, AWSID, bucket, folder, region):
        """
        AWSKEY: str -> Access Key ID for an IAM
        AWSID: str -> Secret Access Key for an IAM
        bucket: str -> Name of bucket being drawn from
        folder: str -> Name of folder where this will grab data from (see note1)
        region: str -> Internal region name for AWS server

        note1:
            In it's current form, this will assume all data on the bucket is 
            being stored in a specific folder within the bucket (e.g. if this 
            is all for PneumaBot all of the relevant data will be under
            manarinth/PneumaBot)

        note2: Regarding taking files for other methods in this class:
            If you are placing the files within subdirectories (or pulling them 
            from local subdirectories) be sure to include that subdirectory
            within the file name (like file='images/Image.jpg')
            DO NOT have a / at the start or end of the file name.
            Use the relative path from the LOCATION OF THE SCRIPT, NOT the CWD.
        """
        self.KEY = AWSKEY
        self.ID = AWSID
        self.bucket = bucket
        self.folder = folder
        self.region = region
        self.client_params = {
            'aws_access_key_id': self.ID, 
            'aws_secret_access_key': self.KEY, 
            'region_name': self.region
        }

    def _req_params(self, file):
        """Short function to get bucket and key kwargs for requests"""
        key = f'{self.folder}/{file}'
        return {"Bucket": self.bucket, "Key": key}

    @HTTPError.catch
    async def get_request(self, file):
        """GET request from S3 storing to local file"""
        print(f'GET Reqeust for: {file}')
        async with aioboto3.client('s3', **self.client_params) as s3:
            save_path = os.path.join(os.path.dirname(__file__), file)
            await s3.download_file(Filename=save_path, **self._req_params(file))
            print('GET Request Completed Successfully')

    @HTTPError.catch
    async def get_raw_request(self, file):
        """GET request from S3 storing to variable as string"""
        print(f'GET Reqeust for: {file} - Returning raw data')
        async with aioboto3.client('s3', **self.client_params) as s3:
            resp = await s3.get_object(**self._req_params(file))
            raw_out = await resp['Body'].read()
            print('GET Request Completed Successfully')
            return raw_out.decode('utf-8')

    @HTTPError.catch
    async def send_request(self, file):
        """PUT requestion for S3 from local file"""
        print(f'PUT Reqeust for: {file}')
        path = os.path.join(os.path.dirname(__file__), file)
        async with aioboto3.client('s3', **self.client_params) as s3:
            await s3.upload_file(Filename=path, **self._req_params(file))
            print('PUT Request Completed Successfully')

    @HTTPError.catch
    async def send_raw_request(self, data, file):
        """PUT request for S3 from variable data"""
        print(f'PUT Reqeust for: {file} - Uploading raw data')
        async with aioboto3.client('s3', **self.client_params) as s3:
            await s3.put_object(Body=data, **self._req_params(file))
            print('PUT Request Completed Successfully')


