from pprint import pprint
import os
from collections import defaultdict

import argparse
import pandas as pd
import tator

import api_util

def add_tator_getloc_args(parser):
    parser.add_argument('--token', required=True, help='A tator api token')
    parser.add_argument('--host', default='https://tator.whoi.edu', help='Tator Server URL, default is "https://tator.whoi.edu"')
    parser.add_argument('--Project', '-p', required=True, help='Project Name or ID. Required.')
    #parser.add_argument('--section', '-s', help='Section Name or ID')    
    parser.add_argument('--media', '-m', nargs='+', help='Media Name or ID')
    parser.add_argument('--frame', '-f', type=int, help='Frame ID')
    parser.add_argument('--loctype', '-l', help='LocalizationType Name or ID')
    parser.add_argument('--version', '-v', nargs='+', help='Version Name or ID')
    parser.add_argument('--att', metavar=('ATT','VAL'), nargs=2, action='append', help='Attribute Equality filter. May be invoked several times. Eg "--att Verified true --att Class diatom"')
    parser.add_argument('--pagination', metavar=('START','STOP'), nargs=2, type=int, help='limit returned results')
    parser.add_argument('--id', help='Either a single Localization ID or a text file listing multiple IDs')
    

def cli():
    parser = argparse.ArgumentParser()
    add_tator_getloc_args(parser)
    
    # TODO also download ROI thumbnail image
    parser.add_argument('--outfile', help='Output CSV')
    
    args = parser.parse_args()
    
    if args.id: 
        if args.id.isdigit():
            args.id = int(args.id)
        elif os.path.isfile(args.id):
            with open(args.id) as f:
                args.id = map(int,f.read().splitlines())
    
    return args


def get_localizations(api, project, versions=None, loctype=None, att_keyval_pairs=None, medias=None, frame=None,
                      startstop:tuple=None, id_list=None):
    created_ids = []
    project = api_util.get_project(api,project)

    kwargs = {}
    # NOTE some params must be wrapped by [list] https://github.com/cvisionai/tator-py/issues/62
    if versions: 
        kwargs['version'] = [api_util.get_version(api, v, project=project.id).id for v in versions]  # can also be a list of int
    if loctype: 
        kwargs['type'] = api_util.get_loctype(api, loctype, project=project.id).id
    if medias: 
        kwargs['media_id'] = [api_util.get_media(api, m).id for m in medias]
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

    pprint(kwargs)  # TODO remove

    if id_list:
        if not isinstance(id_list,list): id_list = [id_list]
        id_list = list(map(int,id_list))
        localization_id_query = tator.models.LocalizationIdQuery(ids=id_list)
        localizations = api.get_localization_list_by_id(project.id, localization_id_query, **kwargs)
    else:
        localizations = api.get_localization_list(project.id, **kwargs)

    return localizations
    
    
def format_localization_dict(api, l):
    d={}
    #media_obj = api_util.get_media(api, l.media)
    d['id'] = l.id
    d['media_id'] = l.media
    d['media'] = api_util.get_media(api, l.media).name
    d['frame'] = l.frame
    #d['frame_tiff'] = os.path.join(media_obj.attributes['tiff_dir'],media_obj.attributes['tiff_pattern'].format(l.frame))
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
        
    api = tator.get_api(args.HOST,args.TOKEN)

    if not args.loctype:
        loctypes = api_util.get_loctype(api, 'list', args.Project)
        assert len(loctypes)==1, 'Multiple Localizations Detected: {'+','.join([f'{lt.id}:{lt.name}' for lt in loctypes])+'}. Specify one with --loctype'
        args.loctype = loctypes[0].id
       
    localizations = get_localizations(api, args.Project, args.version, args.loctype, args.att, args.media, args.frame, args.pagination, args.id)
    
    ## DISPLAY
    loc_dicts = [format_localization_dict(api,loc) for loc in localizations]
    df = pd.DataFrame.from_records(loc_dicts, index='id')
    if args.outfile and args.outfile.endswith('.csv'):
        df.to_csv(args.outfile)
    else:
        print(df.T)
        
            




