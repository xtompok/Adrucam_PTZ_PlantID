import csv
import cv2
from pathlib import Path
from plantid import identify_plant
from s3 import load_key 
import boto3
from botocore.exceptions import ClientError
from autofocus import autofocus,fine_focus,detailed_autofocus 
from enum import Enum, auto
import time

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

PLANT_FIELDS = ('timestamp','prefix','pan','tilt','zoom','focus')

class WorkingMode(Enum):
    SEARCH = auto()
    SNAPSHOT = auto()

class Config(object):
    def __init__(self,prefix,img_dir,bucket,log_filename,plant_filename,api_key,s3cli,delete_img,img_max_retry=5,mode=WorkingMode.SNAPSHOT):
        self.prefix = prefix
        self.img_dir = img_dir
        self.bucket = bucket
        self.log_filename = log_filename
        self.plant_filename = plant_filename
        self.img_max_retry = img_max_retry
        self.api_key = api_key
        self.s3cli = s3cli
        self.delete_img = delete_img
        self.mode = mode

def generate_filename(ctl,timestamp,prefix):
    name = f'p{prefix}_t{timestamp}_P{ctl.get_pan()}_T{ctl.get_tilt()}_Z{int(ctl.get_zoom()*100)}_F{int(ctl.get_focus()*10000)}.jpg'
    return Path(name)

def append_to_log(cfg,ctl,timestamp,laplacian,plant_res):
    data = {
            'timestamp': timestamp,
            'prefix': cfg.prefix,
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

    with open(cfg.log_filename,'a') as f:
        writer = csv.DictWriter(f,fieldnames = LOG_FIELDS)
        writer.writerow(data)

def append_to_plants(cfg,ctl,timestamp):
    data = {
            'timestamp': timestamp,
            'prefix': cfg.prefix,
            'pan': ctl.get_pan(),
            'tilt': ctl.get_tilt(),
            'zoom': ctl.get_zoom(),
            'focus': ctl.get_focus(),
            }
    with open(cfg.plant_filename,'a') as f:
        writer = csv.DictWriter(f,fieldnames = PLANT_FIELDS)
        writer.writerow(data)

def csv_init(cfg):
    with open(cfg.log_filename,'w') as f:
        writer = csv.writer(f)
        writer.writerow(LOG_FIELDS)

    with open(cfg.plant_filename,'w') as f:
        writer = csv.writer(f)
        writer.writerow(PLANT_FIELDS)

def capture(cfg,ctl, cam, pan, tilt, zoom, last_focus):
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
    
    for _ in range(cfg.img_max_retry):
        ret,frame = cam.read()
        timestamp = int(time.time())
        if ret:
            break
    else:
        print("Failed to capture image")

    return timestamp,frame,focus,laplacian

def process_img(cfg,ctl,timestamp,frame,focus,laplacian):

    filepath = cfg.img_dir / generate_filename(ctl, timestamp, cfg.prefix)

    cv2.imwrite(filepath.as_posix(),frame)
    
    try: 
        cfg.s3cli.upload_file(filepath.as_posix(),cfg.bucket,f'{cfg.prefix}/{filepath.name}')
    except ClientError:
        print('Failed to upload {filepath} to S3')
    
    result = identify_plant(filepath,cfg.api_key,timestamp)
    #pp.pprint(result)
    print(f"Is plant: {result['is_plant']} with probability {result['is_plant_probability']}")

    if result['is_plant'] and cfg.mode == WorkingMode.SEARCH:
        append_to_plants(cfg,ctl,timestamp)
        try:
            cfg.s3cli.upload_file(cfg.plant_filename.as_posix(),cfg.bucket,f'{cfg.prefix}/{cfg.plant_filename.name}')
        except ClientError:
            print('Failed to upload {cfg.plant_filename} to S3')

    
    append_to_log(cfg,ctl,timestamp,laplacian,result)
    try:
        cfg.s3cli.upload_file(cfg.log_filename.as_posix(),cfg.bucket,f'{cfg.prefix}/{cfg.log_filename.name}')
    except ClientError:
        print('Failed to upload {cfg.log_filename} to S3')
    if cfg.delete_img:
        filepath.unlink()

