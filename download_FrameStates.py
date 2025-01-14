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

with open('sbatchelder.token') as f: TOKEN=f.read().strip()
api = tator.get_api('https://tator.whoi.edu',TOKEN)
project_id=1
statetype_id=1
version_id=2
statetype=1

states = api.get_state_list(project_id,type=stateype)
records = [dict(id=s.id, media_id=s.media[0], frame=s.frame, modified_by=s.modified_by, modified_ts=s.modified_datetime, Verified=s.attributes['Verified'], training=s.attributes['training'], holdout=s.attributes['holdout']) for s in states]

df = pd.DataFrame.from_records(records)

df['media'] = df.media_id.apply(lambda m: util.get_media(api,m).name.replace('.mp4',''))

df['modified_by'] = df.modified_by.apply(lambda u: util.get_user(api,u).username)

df['tiff_frame'] = df.media_id.apply(lambda m: util.get_media(api,m).attributes['tiff_dir']+'/'+util.get_media(api,m).attributes['tiff_pattern'])
df['tiff_frame'] = df.apply(lambda r: r.tiff_frame.format(r.frame),axis=1)

df = df.sort_values(['media','frame'])
df = df[['id', 'media_id', 'media', 'frame', 'Verified', 'training', 'holdout', 'modified_by', 'modified_ts', 'tiff_frame']]

df.to_csv('oneoff/FrameStates_2023-03-21.csv',index=False)


