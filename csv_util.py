import argparse
import os

import pandas as pd

import tator
from tator.openapi.tator_openapi.models import Localization

import api_util


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', metavar='CSV')
    parser.add_argument('--token', required=True, help='A tator api token')
    parser.add_argument('--host', default='https://tator.whoi.edu',
        help='Tator Server URL, default is "https://tator.whoi.edu"')
    parser.add_argument('--project', '-p', required=True, help='Project Name or ID. Required.')

    parser.add_argument('--col_x', default='x')
    parser.add_argument('--col_y', default='y')
    parser.add_argument('--col_w', default='width')
    parser.add_argument('--col_h', default='height')
    parser.add_argument('--col_class', default='Class')
    parser.add_argument('--col_media', default='media')
    parser.add_argument('--col_frame', default='frame')
    parser.add_argument('--col_imagepath', default='imagepath')

    # TODO: actions
    # convert column coordinates
    # create imagepath column
    # sort
    # add media_id col
    parser.add_argument('--action')

    parser.add_argument('--outfile', help='Output CSV')

    args = parser.parse_args()

    if os.path.isfile(args.token):
        with open(args.token) as f:
            args.token = f.read().strip()

    return args

def xy_corner_to_center(x_corner,y_corner,width,height, pixels_mode=False):
    x_center = x_corner + (width/2)
    y_center = y_corner + (height/2)
    if pixels_mode:
        return round(x_center),round(y_center)
    return x_center,y_center

def xy_center_to_corner(x_corner,y_corner,width,height, pixels_mode=False):
    x_center = x_corner - (width/2)
    y_center = y_corner - (height/2)
    if pixels_mode:
        return round(x_center),round(y_center)
    return x_center,y_center

def pixels_to_ratio(x,y,w,h,img_w,img_h):
    x,w,y,h = x/img_w, w/img_w, y/img_h, h/img_h
    return x,y,w,h
def ratio_to_pixels(x,y,w,h,img_w,img_h):
    x,w,y,h = x*img_w, w*img_w, y*img_h, h*img_h
    return round(x),round(y),round(w),round(h)
def pixel_to_ratio(img_length):
    return lambda pixel: pixel/img_length
def ratio_to_pixel(img_length):
    return lambda ratio: round(ratio*img_length)

if __name__ == '__main__':
    args = cli()
    dtypes = {args.col_media:str, args.col_frame:int,
              args.col_x:float, args.col_y:float,
              args.col_w:float, args.col_h:float}
    df = pd.read_csv(args.src, dtype=dtypes)

    if 'action' == 'tiff_frame':
        api = tator.get_api(args.host, args.token)
        df[args.col_imagepath] = df.apply(lambda l: os.path.join(
            api_util.get_media(api, l[args.col_media]).attributes['tiff_dir'],
            api_util.get_media(api, l[args.col_media]).attributes['tiff_pattern'].format( l['frame'] )
        ))

    if args.outfile and args.outfile.endswith('.csv'):
        df.to_csv(args.outfile, index=False)

