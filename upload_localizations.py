import argparse
import os

from tqdm import tqdm
import pandas as pd
import math
import tator

import api_util


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', metavar='CSV', help='CSV file of localizations to upload')
    parser.add_argument('--host', default='https://tator.whoi.edu', help='Tator Server URL')
    parser.add_argument('--token', required=True, help='A tator api token')
    parser.add_argument('--project', '-p', required=True, help='Name or ID of the Project being uploaded-to')
    parser.add_argument('--loctype', '-l', required=True, help='Name or ID of the LocalizationType being uploaded')
    parser.add_argument('--version', '-v', required=True, help='Name or ID of the Version layer localizations are to be uploaded-to')
    parser.add_argument('--force-version', nargs='?', const=True, help='Create a new version if the named one doesnt already exist. A DESCRIPTION may additionally be provided.')
    parser.add_argument('--col-drop', nargs='+', help='Columns from csv to drop prior to upload')
    parser.add_argument('--col-rename', metavar=('OLD','NEW'), nargs=2, action='append', help='Rename a column. Can be invoked more than once for multiple columns')
    parser.add_argument('--col-add', metavar=('NAME','CONTENT'), nargs=2, action='append', help='Adds a new column NAME populated homogenously with CONTENT. Can be invoked  more than once to create multiple new columns')

    args = parser.parse_args()
    if os.path.isfile(args.token):
        with open(args.token) as f:
            args.token = f.read().strip()

    if args.col_rename:  # must be a dict mapping
        args.col_rename = {v1:v2 for v1,v2 in args.col_rename}

    return args


def make_speclist(api,args):
    speclist = []
    required_headers = 'media,frame,x,y,width,height'.split(',')
    addl_headers = []

    df = pd.read_csv(args.src)
    if args.col_rename:
        df.rename(columns=args.col_rename, inplace=True, errors="raise")
    if args.col_add:
        for col_name,col_content in args.col_add:
            df[col_name] = col_content
    df = df.convert_dtypes()
    print(df.T)
    df = df.sort_values(by=required_headers)

    assert all([item in list(df) for item in required_headers]), 'required headers missing'
    for col in list(df):
        if col not in required_headers and col not in ['version','type'] and col not in args.col_drop:
            addl_headers.append(col)

    for row in df.to_dict(orient="records"):
        spec = {'media_id': api_util.get_media_id(api,row['media'], project=args.project_id),
                'type': args.loctype_id,
                'frame': row['frame'],
                'x': row['x'],
                'y': row['y'],
                'width': row['width'],
                'height': row['height'],
                'version': args.version_id,
               }
        attrib_dict = {}
        for custom_attribute in addl_headers:
            if not isinstance(row[custom_attribute], pd._libs.missing.NAType):
                attrib_dict[custom_attribute] = row[custom_attribute]
                # eg Class, Verified, ModelName, ModelScore
        spec['attributes'] = attrib_dict
        speclist.append(spec)

    return speclist


def upload_speclist(api, speclist, project_id):
    created_ids = []

    # create_localization_list limited to 500 creations per request
    print('Uploading Localizations...')
    speclist500s = [speclist[i:i+500] for i in range(0, len(speclist), 500)]
    for speclist500 in tqdm(speclist500s):
        obj_ids = api.create_localization_list(project_id, speclist500)
        created_ids.extend(obj_ids.id)

    return created_ids




if __name__ == '__main__':
    args = cli()
    api = tator.get_api(args.host, args.token)

    if args.force_version:
        api_util.get_version(api, args.version,
            project=args.project, autocreate=args.force_version)

    api_util.add_arg_ids(api,args)

    speclist = make_speclist(api,args)
    #print(speclist[:2])
    created_ids = upload_speclist(api, speclist, args.project_id)
    print(created_ids)
    
    print(f'DONE! Created {len(created_ids)} localizations')



