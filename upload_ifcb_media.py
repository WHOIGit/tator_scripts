#! /usr/bin/env python

import argparse
import os
from pprint import pprint
import io
import base64
import urllib.request, json 
from time import perf_counter as tictoc

import pandas as pd
import tator



def get_args():
    
    parser = argparse.ArgumentParser()
    parser.add_argument('CSV', help='csv with ifcb "pid,class,score" columns')
    parser.add_argument('--dashboard', default='https://ifcb-data.whoi.edu', help='ifcb dashboard url to pull bin images from')
    #parser.add_argument('--dataset', default='mvco', help='dataset the ifcb csv content belongs to')
    
    tator_args = parser.add_argument_group(title='Tator Parameters', description=None)
    tator_args.add_argument('--host', default='https://tator.whoi.edu', help='Default is "https://tator.whoi.edu"')
    tator_args.add_argument('--token', required=True, help='Tator user-access token (required)')
    #tator_args.add_argument('--project_id', type=int, default=5, help='Default is "5" for the IFCB project')  # isiis
    tator_args.add_argument('--media_type_id', type=int, default=7, help='Default is "7" for ROI')

    args = parser.parse_args()
    
    return args


if __name__ == '__main__':
    download_time = 0
    todisk_time = 0
    upload_time = 0

    # 0) inputs: CSV, ifcb dashboard params, tator_configs
    args = get_args()
    api = tator.get_api(args.host, args.token)
    
    # 1) ingest csv
    df = pd.read_csv(args.CSV)
    #df['url'] = df.pid.apply(lambda pid:f'{args.dashboard}/{args.dataset}/{pid}.png')
    new = df.pid.str.rsplit("_", n=1, expand=True)
    df['bin'],df['roi_num'] = new[0],new[1]
    df['url'] = df[['bin','roi_num']].apply(lambda row: f'{args.dashboard}/api/image_data/{row.bin}/{row.roi_num}', axis=1)
    
    start_time = tictoc()
    
    for idx,row in df.iterrows():
        print(idx, row.bin, row.roi_num, end=' ... ', flush=True)
        # 2) download image locally
        local_fname = f'tator_transcode_workspace/{row.pid}.png'
        tic = tictoc()
        with urllib.request.urlopen(row.url) as url:
            content = json.load(url)
            img_data = content['data']
        download_time += tictoc()-tic
        
        # 3) save img to disk
        tic = tictoc()
        with open(local_fname, "wb") as f:
            f.write(base64.b64decode(img_data))
        todisk_time += tictoc()-tic
        
        # 4) create attributes dict
        attribs = {'pid':row['pid'],
                   'bin':row['bin'],
                   'Class':row['class'], 
                   'ModelScore':row['score'],
                  }
        # 5) upload to tator
        tic = tictoc()
        for progress, response in tator.util.upload_media(api, args.media_type_id, path=local_fname, attributes=attribs):
            pass
            #print(f"{idx} - Upload progress for {row.pid}: {progress}%")
        upload_time += tictoc()-tic
        print(response.message)
        
        # 6) remove downloaded image
        os.remove(local_fname)
        
    total_time = tictoc()-start_time
    print(f'Download: {download_time}s ({download_time/total_time:.1%})')
    print(f'ToDisk: {todisk_time}s ({todisk_time/total_time:.1%})')
    print(f'Upload: {upload_time}s ({upload_time/total_time:.1%})')
    

