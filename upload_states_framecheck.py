#! /usr/bin/env python

import os
import argparse
import pandas as pd
import tator
from tator.openapi.tator_openapi.models import StateSpec

import api_util

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('CSV', help='csv with ifcb "pid,class,score" columns')

    tator_args = parser.add_argument_group(title='Tator Parameters', description=None)
    tator_args.add_argument('--host', default='https://tator.whoi.edu', help='Default is "https://tator.whoi.edu"')
    tator_args.add_argument('--token', required=True, help='Tator user-access token (required)')
    parser.add_argument('--project', '-p', required=True, help='Name or ID of the Project (required)')
    #parser.add_argument('--version', '-v', required=True, help='Name or ID of the Version (required)')
    #parser.add_argument('--statetype', '-s', required=True, help='Name or ID of the StateType (required)')

    return parser

def cli():
    parser = get_parser()
    args = parser.parse_args()

    if os.path.isfile(args.token):
        with open(args.token) as f:
            args.token = f.read().strip()

    return args


if __name__ == '__main__':


    # 0) inputs: CSV, state type and version
    args = cli()
    api = tator.get_api(args.host, args.token)
    args.project_id = api_util.get_project_id(api, args.project)
    #args.version_id = api_util.get_version(api, args.version, project=args.project_id).id
    #args.statetype_id = api_util.get_statetype(api,args.statetype,project=args.project_id).id
    
    # 1) ingest csv
    df = pd.read_csv(args.CSV)
    # make a data object for state verifieds

    # 3) for each instance, create a tator StateSpec
    speclist = []
    required_headers = 'media_id,frame,statetype_id,version_id'.split(',')
    addl_headers = []
    df = df.sort_values(by=required_headers)

    assert all([item in list(df) for item in required_headers]), 'required headers missing'
    for col in list(df):
        if col not in required_headers:
            addl_headers.append(col)
    
    for idx,row in df.iterrows():
        attrib_dict = {}
        for custom_attribute in addl_headers:
            if not isinstance(row[custom_attribute], pd._libs.missing.NAType):
                attrib_dict[custom_attribute] = row[custom_attribute]
        spec = StateSpec(frame=row.frame,
                         media_ids=[row.media_id],
                         type=row.statetype_id,
                         version=row.version_id,
                         attributes=attrib_dict)

        speclist.append(spec)

    # 2) upload to tator
    speclist500s = [speclist[i:i+500] for i in range(0, len(speclist), 500)]
    for speclist500 in speclist500s:
        obj_ids = api.create_state_list(args.project_id, speclist500)
        print(obj_ids)

    print('Done')

    

