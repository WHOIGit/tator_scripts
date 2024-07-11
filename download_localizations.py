from pprint import pprint
import os
from collections import defaultdict

import argparse
import pandas as pd
import tator
from tator.openapi.tator_openapi.models import Localization
from tqdm import tqdm
import shutil
import api_util

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', required=True, help='A tator api token')
    parser.add_argument('--host', default='https://tator.whoi.edu',  help='Tator Server URL, default is "https://tator.whoi.edu"')
    parser.add_argument('--project', '-p', required=True, help='Project Name or ID. Required.')
    # parser.add_argument('--section', '-s', help='Section Name or ID')
    parser.add_argument('--media', '-m', help='Media Name or ID')
    parser.add_argument('--frame', '-f', type=int, help='Frame ID')
    parser.add_argument('--loctype', '-l', help='LocalizationType Name or ID')
    parser.add_argument('--version', '-v', help='Version Name or ID')
    parser.add_argument('--att', metavar=('ATT', 'VAL'), nargs=2, action='append',
        help='Attribute Equality filter. May be invoked several times. Eg "--att Verified true --att Class diatom"')
    parser.add_argument('--pagination', metavar=('START', 'STOP'), nargs=2, type=int, help='limit returned results')
    parser.add_argument('--id', help='Either a single Localization ID or a text file listing multiple IDs')
    parser.add_argument('--statetype', help='StateType Name or ID to filter Localizations by frame. Cannot be used with FRAME, PAGINATION, or ID')
    parser.add_argument('--state-att', nargs=2, action='append', help='Further filter states by attribute equality')
    parser.add_argument('--chips-download-dir', help='Directory to download localization chips (thumbnails) to')
    parser.add_argument('--frame-download-dir', help='Directory to download frames to')

    parser.add_argument('--outfile', help='Output CSV')
    
    args = parser.parse_args()

    if os.path.isfile(args.token):
        with open(args.token) as f:
            args.token = f.read().strip()

    if args.id: 
        if args.id.isdigit():
            args.id = int(args.id)
        elif os.path.isfile(args.id):
            with open(args.id) as f:
                args.id = map(int,f.read().splitlines())
    
    return args


def get_localizations(api, project, versions=None, loctype=None, att_keyval_pairs=None, media=None, frame=None,
                      startstop:tuple=None, id_list=None):
    created_ids = []
    project = api_util.get_project(api,project)

    kwargs = {}
    # NOTE some params must be wrapped by [list] https://github.com/cvisionai/tator-py/issues/62
    if versions: 
        kwargs['version'] = [api_util.get_version(api, v, project=project.id).id for v in versions]  # can also be a list of int
    if loctype: 
        kwargs['type'] = api_util.get_loctype(api, loctype, project=project.id).id
    if media:
        kwargs['media_id'] = [api_util.get_media(api, media).id]
    if frame:  
        kwargs['frame'] = int(frame)
    #if section: 
    #    kwargs['section'] = api_util.get_section(api,section).id
        
    if att_keyval_pairs:
        kwargs['attribute'] = [f'{att}::{val}' for att,val in att_keyval_pairs]
    # attribute (list[str**]) - Attribute equality filter. 
    #     _lt _lte _gt _gte _contains _null 
    #     Format is attribute1::value1,[attribute2::value2].
    
    # media_search (str) - lucene query for elasticsearch
    # search (str) - lucene query for elasticsearch 

    if startstop:
        kwargs['start'] = int(startstop[0])
        kwargs['stop'] = int(startstop[1])

    #pprint(kwargs)  # TODO remove

    if id_list:
        if not isinstance(id_list,list): id_list = [id_list]
        id_list = list(map(int,id_list))
        localization_id_query = tator.models.LocalizationIdQuery(ids=id_list)
        localizations = api.get_localization_list_by_id(project.id, localization_id_query, **kwargs)
    else:
        localizations = api.get_localization_list(project.id, **kwargs)

    return localizations


def format_localization_dict(api, l:Localization):
    d = dict()
    media_obj = api_util.get_media(api, l.media)
    d['id'] = l.id
    d['media_id'] = l.media
    d['media'] = api_util.get_media(api, l.media).name
    d['frame'] = l.frame
    if 'tiff_dir' in media_obj.attributes and 'tiff_pattern' in media_obj.attributes:
        d['frame_tiff'] = os.path.join(media_obj.attributes['tiff_dir'],media_obj.attributes['tiff_pattern'].format(l.frame))
    d['version_id'] = l.version
    d['version'] = api_util.get_version(api, l.version).name
    #d['created_by'] = api.get_user(l.created_by).username if l.created_by else ''
    #d['created_datetime'] = l.created_datetime.isoformat(timespec='seconds') if l.created_datetime else ''
    d['modified_by'] = api.get_user(l.modified_by).username if l.modified_by else ''
    d['modified_datetime'] = l.modified_datetime.isoformat(timespec='seconds') if l.modified_datetime else ''
    for att in 'x y width height'.split():
        d[att] = getattr(l,att)
    d.update(l.attributes)
    return d


if __name__=='__main__':
    args = cli()
    api = tator.get_api(args.host,args.token)

    if not args.loctype:
        loctypes = api_util.get_loctype(api, 'list', args.project)
        assert len(loctypes)==1, 'Multiple Localization Types Detected: {'+','.join([f'{lt.id}:{lt.name}' for lt in loctypes])+'}. Specify one with --loctype'
        args.loctype = loctypes[0].id

    print('Fetching localizations...')
    if args.statetype:
        project_id = api_util.get_project_id(api, args.project)
        version_ids = [api_util.get_version(api, args.version).id] if args.version else None
        media_ids = [api_util.get_media(api, args.media).id] if args.media else None
        statetype = api_util.get_statetype(api, args.statetype, project=project_id)
        eq_attribs = [f'{key}::{val}' for key,val in args.state_att]
        states = api.get_state_list(project_id, type=statetype.id, version=version_ids, media_id=media_ids, attribute=eq_attribs )
        localizations = []
        media_frame_dict = defaultdict(list)
        for state in states:
            media_frame_dict[state.media[0]].append(state.frame)
        for media_id,frames in tqdm(media_frame_dict.items()):
            for frame in tqdm(frames, leave=False):
                locs = get_localizations(api, args.project, [args.version], args.loctype, args.att, media_id, frame)
                localizations.extend(locs)

    else:
        localizations = get_localizations(api, args.project, [args.version], args.loctype, args.att, args.media, args.frame, args.pagination, args.id)

    ## DISPLAY
    print('Building CSV')
    loc_dicts = [format_localization_dict(api,loc) for loc in localizations]
    df = pd.DataFrame.from_records(loc_dicts, index='id')
    if args.frame_download_dir:
        df['imagepath'] = df.apply(lambda row: os.path.join(args.frame_download_dir,f'{row.media_id}_{row.frame}.png'), axis=1)
    if args.outfile and args.outfile.endswith('.csv'):
        print('Saving CSV to:', args.outfile)
        df.to_csv(args.outfile, index=False)
    else:
        print(df.T)

    if args.frame_download_dir:
        print('Downloading Frames to:', args.frame_download_dir)
        os.makedirs(args.frame_download_dir, exist_ok=True)

        for l in tqdm(localizations):
            target_img_name = f'{l.media}_{l.frame}.png'
            target_img_path = os.path.join(args.frame_download_dir,target_img_name)
            if not os.path.isfile(target_img_path):  # todo clobber? but then what about keeping track of repeat frames
                tmp_img_path = api.get_frame(l.media, frames=[l.frame])
                shutil.copyfile(tmp_img_path,target_img_path)

    if args.chips_download_dir:
        print('Downloading localization images to:', args.chips_download_dir)
        os.makedirs(args.chips_download_dir, exist_ok=True)
        for l in tqdm(localizations):
            target_img_name = f'{l.media}_{l.frame}_{l.id}.png'
            target_img_path = os.path.join(args.chips_download_dir,target_img_name)
            if not os.path.isfile(target_img_path):  # todo clobber?
                tmp_img_path = api.get_localization_graphic(l.id)
                shutil.copyfile(tmp_img_path, target_img_path)





