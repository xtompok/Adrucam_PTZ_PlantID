#!/usr/bin/env python3

import boto3
import click
from pathlib import Path

RAMDISK = Path('/tmp/ram')
BUCKET = 'plantid-origami'

def load_key(s3key):
    access = None
    secret = None
    
    for line in s3key:
        (name,val) = line.split(':')
        if name.strip().lower() == 'access':
            access = val.strip()
        if name.strip().lower() == 'secret':
            secret = val.strip()

    return access, secret

@click.command()
@click.option('--s3key', help='Path to the file with S3 key', required=True, type=click.File('r'))
def main(s3key):
    access,secret = load_key(s3key)
    s3cli = boto3.client('s3',aws_access_key_id = access, aws_secret_access_key = secret)
    filename = RAMDISK/Path('tmp_test.txt')
    with open(str(filename),'w') as f:
        f.write('Test file\n')

    s3cli.upload_file(str(filename),BUCKET,filename.name)

    
if __name__ == '__main__':
    main()
