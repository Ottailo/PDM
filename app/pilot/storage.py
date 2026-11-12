"""Private blobs; no public static path or unauthenticated download URL."""
import os
import re
from pathlib import Path
from flask import current_app


class LocalStorage:
    def __init__(self,root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)

    def path(self,key):
        if not re.fullmatch(r'[a-f0-9]{32}\.pdf',key):
            raise ValueError('Invalid private blob key')
        path = self.root/key
        if path.is_symlink():
            raise ValueError('Symlinks are not permitted in private storage')
        return path

    def put(self,key,content):
        path = self.path(key)
        descriptor = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'wb') as file:
            file.write(content)

    def get(self,key,maximum):
        with self.path(key).open('rb') as file:
            content = file.read(maximum+1)
        if len(content)>maximum:
            raise ValueError('Private blob exceeds size limit')
        return content

    def delete(self,key):
        self.path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self,config):
        import boto3
        self.bucket = config['S3_BUCKET']
        self.client = boto3.client('s3',endpoint_url=config.get('S3_ENDPOINT_URL') or None,region_name=config.get('S3_REGION') or None)

    def key(self,key):
        if not re.fullmatch(r'[a-f0-9]{32}\.pdf',key):
            raise ValueError('Invalid private blob key')
        return 'pilot-private/'+key

    def put(self,key,content):
        self.client.put_object(Bucket=self.bucket,Key=self.key(key),Body=content,ContentType='application/pdf',ServerSideEncryption='AES256')

    def get(self,key,maximum):
        response = self.client.get_object(Bucket=self.bucket,Key=self.key(key))
        try:
            if response['ContentLength']>maximum:
                raise ValueError('Private blob exceeds size limit')
            content = response['Body'].read(maximum+1)
        finally:
            response['Body'].close()
        if len(content)>maximum:
            raise ValueError('Private blob exceeds size limit')
        return content

    def delete(self,key):
        self.client.delete_object(Bucket=self.bucket,Key=self.key(key))


def storage():
    return current_app.extensions['pilot_storage']
