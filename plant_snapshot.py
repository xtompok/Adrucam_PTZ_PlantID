#!/usr/bin/env python3

from capture import open_camera
from control import Controller
from autofocus import autofocus,fine_focus,detailed_autofocus 
import time
from pathlib import Path
import click
import pprint
import boto3
import csv
from s3 import load_key
from plant_utils import csv_init, capture, process_img, Config

PREFIX = 'test'
BUCKET = 'plantid-origami'

STORAGE_DIR = Path('/tmp/ram')
IMG_DIR = Path('/tmp/ram')
LOG_CSV_FILENAME = STORAGE_DIR / Path('snapshot_results.csv')
PLANT_CSV_FILENAME = STORAGE_DIR / Path('plants.csv')

pp = pprint.PrettyPrinter(width=200)


@click.command()
@click.option('--apikey', help='Path to the file with API key', required=True, type=click.File('r'))
@click.option('--s3key', help='Path to the file with S3 key', required=True, type=click.File('r'))
@click.option('--prefix', help='Prefix for captured data')
@click.option('--delete-img/--no-delete-img','-d','delete_img', help='Delete images after upload?')
def main(apikey,s3key,prefix,delete_img):
    # Process arguments
    if prefix is None:
        prefix = PREFIX

    apikey = apikey.read().strip()

    access,secret = load_key(s3key)
    s3cli = boto3.client('s3',aws_access_key_id = access, aws_secret_access_key = secret)

    # Create config object
    cfg = Config(prefix=prefix, img_dir=IMG_DIR, bucket=BUCKET, log_filename=LOG_CSV_FILENAME,
            plant_filename=PLANT_CSV_FILENAME, api_key=apikey, s3cli=s3cli, delete_img=delete_img)

    # Prepare camera and controller
    ctl = Controller(1)
    ctl.print_status()

    cam = open_camera() 

    with open(PLANT_CSV_FILENAME) as f:
        reader = csv.DictReader(f)
        plants = [row for row in reader]

    if not plants:
        print("No plants in the list, exitting")
        return

    for plant in plants:
        print("Capturing {plant}")
        timestamp,frame,last_focus,laplacian = capture(cfg,ctl,cam,int(plant['pan']),int(plant['tilt']),float(plant['zoom']),float(plant['focus']))
        process_img(cfg,ctl,timestamp,frame,last_focus,laplacian)



if __name__ == '__main__':
    main()
