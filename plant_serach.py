#!/usr/bin/env python3

import cv2
from capture import open_camera
from control import Controller
from autofocus import autofocus,fine_focus,detailed_autofocus 
from s3 import load_key 
import boto3
from botocore.exceptions import ClientError
import time
from pathlib import Path
import click
import requests
import base64
import csv
import pprint

STEP = 5
DELAY = 0.5
MIN_TILT = 15
MAX_TILT = 165
MIN_PAN = 0
MAX_PAN = 180
ZOOM = 0.5

IMG_MAX_RETRY = 5

PREFIX = 'test'
BUCKET = 'plantid-origami'

STORAGE_DIR = Path('/tmp/ram')
IMG_DIR = Path('/tmp/ram')
LOG_CSV_FILENAME = STORAGE_DIR / Path('results.csv')
LOG_FIELDS = ('timestamp','prefix','pan','tilt','zoom','focus','laplacian',
'pid_id',
'pid_plant_name',
'pid_probability',
'pid_is_plant_probability',
'pid_is_healthy_probability',
'pid_diseases_0_entity_id',
'pid_diseases_0_probability',
'pid_diseases_0_name',
'pid_diseases_1_entity_id',
'pid_diseases_1_probability',
'pid_diseases_1_name',)

PLANT_CSV_FILENAME = STORAGE_DIR / Path('plants.csv')
PLANT_FIELDS = ('timestamp','prefix','pan','tilt','zoom','focus')

pp = pprint.PrettyPrinter(width=200)

def generate_filename(ctl,timestamp,prefix):
    name = f'p{prefix}_t{timestamp}_P{ctl.get_pan()}_T{ctl.get_tilt()}_Z{int(ctl.get_zoom()*100)}_F{int(ctl.get_focus()*10000)}.jpg'
    return Path(name)

def append_to_log(ctl,timestamp,prefix,laplacian,plant_res):
    data = {
            'timestamp': timestamp,
            'prefix': prefix,
            'pan': ctl.get_pan(),
            'tilt': ctl.get_tilt(),
            'zoom': ctl.get_zoom(),
            'focus': ctl.get_focus(),
            'laplacian': laplacian,
            'pid_id': plant_res['id'],
            'pid_is_plant_probability': plant_res['is_plant_probability'],
            'pid_is_healthy_probability': plant_res['health_assessment']['is_healthy_probability'],
            }
    if plant_res['suggestions']:
        data['pid_plant_name'] = plant_res['suggestions'][0]['plant_name']
        data['pid_probability'] = plant_res['suggestions'][0]['probability']
    if plant_res['health_assessment']['diseases']:
        data['pid_diseases_0_entity_id'] = plant_res['health_assessment']['diseases'][0]['entity_id']
        data['pid_diseases_0_probability'] = plant_res['health_assessment']['diseases'][0]['probability']
        data['pid_diseases_0_name'] =  plant_res['health_assessment']['diseases'][0]['name']
    if len(plant_res['health_assessment']['diseases']) > 1:
        data['pid_diseases_1_entity_id'] = plant_res['health_assessment']['diseases'][1]['entity_id']
        data['pid_diseases_1_probability'] = plant_res['health_assessment']['diseases'][1]['probability']
        data['pid_diseases_1_name'] =  plant_res['health_assessment']['diseases'][1]['name']

    with open(LOG_CSV_FILENAME,'a') as f:
        writer = csv.DictWriter(f,fieldnames = LOG_FIELDS)
        writer.writerow(data)

def append_to_plants(ctl,timestamp,prefix):
    data = {
            'timestamp': timestamp,
            'prefix': prefix,
            'pan': ctl.get_pan(),
            'tilt': ctl.get_tilt(),
            'zoom': ctl.get_zoom(),
            'focus': ctl.get_focus(),
            }
    with open(PLANT_CSV_FILENAME,'a') as f:
        writer = csv.DictWriter(f,fieldnames = PLANT_FIELDS)
        writer.writerow(data)

def csv_init():
    with open(LOG_CSV_FILENAME,'w') as f:
        writer = csv.writer(f)
        writer.writerow(LOG_FIELDS)
        
    with open(PLANT_CSV_FILENAME,'w') as f:
        writer = csv.writer(f)
        writer.writerow(PLANT_FIELDS)


def encode_file(file_name):
    with open(file_name, "rb") as file:
        return base64.b64encode(file.read()).decode("ascii")


def identify_plant(filename,api_key):
    # see the docs for more optional attributes
    params = {
        "api_key": api_key,
        "images": [encode_file(filename)],
        "datetime": int(time.time()),
        # modifiers docs: https://github.com/flowerchecker/Plant-id-API/wiki/Modifiers
        "modifiers": ["crops_fast", "similar_images", "health_all", "disease_similar_images"],
        "plant_language": "en",
        # plant details docs: https://github.com/flowerchecker/Plant-id-API/wiki/Plant-details
        "plant_details": ["common_names",
                          "edible_parts",
                          "gbif_id"
                          "name_authority",
                          "propagation_methods",
                          "synonyms",
                          "taxonomy",
                          "url",
                          "wiki_description",
                          "wiki_image",
                          ],
        # disease details docs: https://github.com/flowerchecker/Plant-id-API/wiki/Disease-details
        "disease_details": ["common_names", "url", "description"]
        }

    headers = {
        "Content-Type": "application/json"
        }

    response = requests.post("https://api.plant.id/v2/identify",
                             json=params,
                             headers=headers)
    return response.json()





def capture(ctl, cam, pan, tilt, zoom, api_key, s3cli, delete_img, last_focus):
    ctl.set_tilt(tilt)
    time.sleep(0.01)
    ctl.set_pan(pan)
    time.sleep(0.01)
    ctl.set_zoom(zoom)
    time.sleep(0.01)
    
    laplacian = None
    # We got focus from previous frame, try to search around it
    if last_focus:
        focus,laplacian = fine_focus(ctl,cam,last_focus,0.2)
        if laplacian:
            print(f'Fast focusing: focus:{focus:.3f}, laplac: {laplacian:.3f}')
        else: 
            print("Fast focusing failed")
    
    # If previous fail or we don't have focus hint, make full focusing
    if not last_focus or not laplacian or laplacian < 50:
        focus, laplacian = autofocus(ctl,cam)
        if laplacian:
            print(f'Full focusing: focus:{focus:.3f}, laplac: {laplacian:.3f}')
        else:
            print("Full focusing failed")
#            focus,laplacian = detailed_autofocus(ctl,cam) 
#            print(f"Detailed: {focus},{laplacian}")
    
    for _ in range(IMG_MAX_RETRY):
        ret,frame = cam.read()
        timestamp = int(time.time())
        if ret:
            break
    else:
        print("Failed to capture image")

    filepath = IMG_DIR / generate_filename(ctl, timestamp, PREFIX)

    cv2.imwrite(filepath.as_posix(),frame)
    
    try: 
        s3cli.upload_file(filepath.as_posix(),BUCKET,f'{PREFIX}/{filepath.name}')
    except ClientError:
        print('Failed to upload {filepath} to S3')
    
    result = identify_plant(filepath,api_key)
    #pp.pprint(result)
    print(f"Is plant: {result['is_plant']} with probability {result['is_plant_probability']}")

    if result['is_plant']:
        append_to_plants(ctl,timestamp,PREFIX)
        try:
            s3cli.upload_file(PLANT_CSV_FILENAME.as_posix(),BUCKET,f'{PREFIX}/{PLANT_CSV_FILENAME.name}')
        except ClientError:
            print('Failed to upload {PLANT_CSV_FILENAME} to S3')

    
    append_to_log(ctl,timestamp,PREFIX,laplacian,result)
    try:
        s3cli.upload_file(LOG_CSV_FILENAME.as_posix(),BUCKET,f'{PREFIX}/{LOG_CSV_FILENAME.name}')
    except ClientError:
        print('Failed to upload {LOG_CSV_FILENAME} to S3')
    if delete_img:
        filepath.unlink()

    return focus



@click.command()
@click.option('--apikey', help='Path to the file with API key', required=True, type=click.File('r'))
@click.option('--s3key', help='Path to the file with S3 key', required=True, type=click.File('r'))
@click.option('--prefix', help='Prefix for captured data')
@click.option('--delete-img/--no-delete-img','-d','delete_img', help='Delete images after upload?')
@click.option('--init',is_flag=True, confirmation_prompt=True, help='Truncate and reinit CSV files')
def main(apikey,s3key,prefix,delete_img,init):
    # Process arguments
    if prefix is not None:
        PREFIX = prefix

    apikey = apikey.read().strip()

    access,secret = load_key(s3key)
    s3cli = boto3.client('s3',aws_access_key_id = access, aws_secret_access_key = secret)

    if init:
        csv_init()

    # Prepare camera and controller
    ctl = Controller(1)
    ctl.print_status()

    cam = open_camera() 

    ctl.set_zoom(ZOOM)

    last_focus = None

    # Scan
    for tilt in range(MIN_TILT,MAX_TILT,2*STEP):
        for pan in range(MIN_PAN,MAX_PAN,STEP):
            print(f"Pan: {pan}, tilt: {tilt}")
            last_focus = capture(ctl,cam,pan,tilt,ZOOM,apikey,s3cli,delete_img,last_focus)

        tilt += STEP
        time.sleep(0.01)
        for pan in range(MAX_PAN,MIN_PAN,-STEP):
            print(f"Pan: {pan}, tilt: {tilt}")
            last_focus = capture(ctl,cam,pan,tilt,ZOOM,apikey,s3cli,delete_img,last_focus)


if __name__ == '__main__':
    main()
