#!/usr/bin/env python3

import cv2
from capture import gstreamer_pipeline
from control import Controller
import time
from pathlib import Path
import click
import requests
import base64

STEP = 5
DELAY = 0.5
MIN_TILT = 15
MAX_TILT = 165
MIN_PAN = 0
MAX_PAN = 180

IMG_MAX_RETRY = 5

STORAGE_DIR = Path('/tmp/ram')

def generate_filename(pan, tilt, ir=False):
    return Path(f"{pan}_{tilt}_ir{int(ir)}_{int(time.time()*10)}.jpg")

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





def capture(ctl, cam, api_key, pan,tilt,ir,delay):
    ctl.set_tilt(tilt)
    time.sleep(0.01)
    ctl.set_pan(pan)
    time.sleep(delay)
    
    for _ in range(IMG_MAX_RETRY):
        ret,frame = cam.read()
        if ret:
            break
    else:
        print("Failed to capture image")

    filepath = STORAGE_DIR / generate_filename(pan,tilt,ir)

    cv2.imwrite(filepath.as_posix(),frame)
    result = identify_plant(filepath,api_key)
    print(f"Is plant: {result['is_plant']} with probability {result['is_plant_probability']}")



@click.command()
@click.option('--apikey', help='Path to the file with API key', required=True, type=click.File('r'))
def main(apikey):

    apikey = apikey.read().strip()

    ctl = Controller(1)
    ctl.print_status()

    cam = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

    for tilt in range(MIN_TILT,MAX_TILT,2*STEP):
        for pan in range(MIN_PAN,MAX_PAN,STEP):
            print(f"Pan: {pan}, tilt: {tilt}")
            capture(ctl,cam,apikey,pan,tilt,False,DELAY)

        tilt += STEP
        time.sleep(0.01)
        for pan in range(MAX_PAN,MIN_PAN,-STEP):
            print(f"Pan: {pan}, tilt: {tilt}")
            capture(ctl,cam,apikey,pan,tilt,False,DELAY)


if __name__ == '__main__':
    main()
