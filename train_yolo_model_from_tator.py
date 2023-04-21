import os, sys
import tempfile 
from collections import defaultdict
import yaml
import random
from pprint import pprint

import argparse
import tator

import api_util
from annotation_download import get_localizations, add_tator_getloc_args, format_localization_dict
import yolov5_ultralytics.train

def cli():
    parser = argparse.ArgumentParser()
    
    # Tator Localization Argument Group 
    tator_getloc_arggroup = parser.add_argument_group('Tator Localization Params')
    add_tator_getloc_args(tator_getloc_arggroup)
    
    # Yolo dataset Params
    yolo_dataset_group = parser.add_argument_group('Tator Localization Params')
    yolo_dataset_group.add_argument('--classes', default='auto', help='A listfile of class labels')
    yolo_dataset_group.add_argument('--datadir', default='/dev/shm', help='Where to save yolo training files. Eg: "/tmp". Default is "/dev/shm" ie ramdisk')
    yolo_dataset_group.add_argument('--persist', action='store_true', help='When invoked, DATADIR will persist after program runs')
    yolo_dataset_group.add_argument('--split', metavar='RATIO', default=0.8, type=float, help='Ratio of training images vs. validation images. Default is "0.8" ie 80:20 TRAIN:VAL split. Frames are split-up such as to distribute class localizations according to this ratio as best as possible.')
    
    # Yolo Training Params
    yolo_train_group = parser.add_argument_group('Tator Training Params')
    yolo_train_group.add_argument('--skip-training', action='store_true', help='Actually, dont train a model')
    yolov5_ultralytics.train.add_yolo_train_args(yolo_train_group)
    
    args = parser.parse_args()
    
    if args.id: 
        if args.id.isdigit():
            args.id = int(args.id)
        elif os.path.isfile(args.id):
            with open(args.id) as f:
                args.id = map(int,f.read().splitlines())
    
    if os.path.isfile(args.classes):
        with open(args.classes) as f:
            args.classes = f.read().splitlines()
                
    return args


def trainval_split(frames:list, training_ratio:float):
    training_frames_total = round(training_ratio*len(frames))
    shuffled_frames = frames[:]
    random.shuffle(shuffled_frames)
    return shuffled_frames[:training_frames_total], shuffled_frames[training_frames_total:]
    

def make_dataset_yaml(root, train_txt, val_txt, class_labels, test_txt=None, output=None):
    template = '''
    # Train/val/test sets
    path: {ROOT}         # ramdisk or regular filesystem path
    train: {TRAIN_TXT}   # relative to ROOT
    val: {VAL_TXT}       # relative to ROOT
    test: {TEST_TXT}     # (optional)

    # Classes
    names:
      0: Akashiwo
      1: diatom
      2: whatever
    '''
    yaml_data = dict(path=root, train=train_txt, val=val_txt,
                     names={idx:val for idx,val in enumerate(class_labels)})
    if test_txt:
        yaml_data['test'] = test_txt
    
    if output:
        with open(output, 'w') as f:
            yaml.dump(yaml_data,f)
    else:
        return yaml.dump(yaml_data)



if __name__=='__main__':
    args = cli()
    if args.data and not args.skip_training:
        yolov5_ultralytics.train.main(args)
        sys.exit()
    api = tator.get_api(args.host, args.token)

    #1 collect localizations and frames from tator
    print('Collecting Localizations from Tator')
    localizations = get_localizations(api, args.Project, args.version, args.loctype, args.att, args.media, args.frame, args.pagination, args.id)
    localizations = [format_localization_dict(api, l) for l in localizations]
    #TODO collect verified frames that DO NOT have localizations in them
    
    #2 check all frames are accessible on disk and group to tiff_frames
    print('Checking for Frames on-disk')
    missing_tiffs = []
    locs_per_frame = defaultdict(list)
    tator_classes = set()
    for l in localizations:
        media_obj = api_util.get_media(api, l['media_id'])
        tiff_frame = os.path.join(media_obj.attributes['tiff_dir'],media_obj.attributes['tiff_pattern'].format(l['frame']))
        l['tiff_frame'] = tiff_frame
        if not os.path.isfile(tiff_frame):
            missing_tiffs.append(l)
        locs_per_frame[tiff_frame].append(l)
        tator_classes.add(l['Class'])
    error_str = "Can't find tiff frames:\n  " + '  \n'.join([l['tiff_frame'] for l in missing_tiffs])
    assert not missing_tiffs, error_str
    
    #3 create ramdisk
    print(f'Setting up datadir: {args.datadir}')
    if args.persist:
        if os.path.isdir(args.datadir): 
            import shutil
            shutil.rmtree(args.datadir)
        os.makedirs(args.datadir)
    else:
        tmpdir = tempfile.TemporaryDirectory(dir=args.datadir, prefix='yolodata_',) # ramdisk
        args.datadir = tmpdir.name
    images_dir = os.path.join(args.datadir,'images')
    labels_dir = os.path.join(args.datadir,'labels')
    os.mkdir(images_dir)
    os.mkdir(labels_dir)
    
    #4 create symlinks from frames on disk to ramdisk:/images
    loccount_perclass_persymframe = defaultdict(lambda:  defaultdict(int))  # d[framefile_n][classlabel_x]=0
    tator_classes = sorted(tator_classes)
    if args.classes=='auto':
        args.classes = tator_classes
    
    sym_frames = []
    for realpath,localizations in locs_per_frame.items():
        frame_filename = os.path.basename(realpath)
        sym_frame = os.path.join(images_dir,frame_filename)
        os.symlink(realpath,sym_frame)     
        sym_frames.append(sym_frame)
        
        #5 create label files on ramdisk:/labels for localizations for all frames 
        # format: class x_center y_center width height
        label_filename = os.path.splitext(frame_filename)[0]+'.txt'
        label_file = os.path.join(labels_dir,label_filename)
        with open(label_file, 'w') as f:
            for l in localizations:
                class_idx = args.classes.index(l['Class'])
                center_x = l['x'] + l['width']/2
                center_y = l['y'] + l['height']/2
                f.write(f"{class_idx} {center_x} {center_y} {l['width']} {l['height']}\n")
                loccount_perclass_persymframe[frame_filename][l['Class']] += 1
                    
    #6 split frames into train and val lists, create train.txt and val.txt respectively
    print('Distributing Frames to Training and Validation datasets')
    #TODO split frames PERCLASS somehow
    #TODO check for class mismatches between tator locs and args.classes
    cwd = os.getcwd()
    sym_frames = [os.path.join(cwd,frame) for frame in sym_frames]
    train_frames, val_frames = trainval_split(sym_frames,args.split)
    train_txt = 'train.txt'
    val_txt = 'val.txt'
    train_file = os.path.join(args.datadir,train_txt)
    val_file = os.path.join(args.datadir, val_txt)
    with open(train_file, 'w') as f:
        f.write('\n'.join(train_frames))
    with open(val_file, 'w') as f:
        f.write('\n'.join(val_frames))
          
    #7 report metrics
    classcounts = defaultdict(lambda: defaultdict(int))
    print('CLASSES:')
    for frame in train_frames:
        frame = os.path.basename(frame)
        for cls,count in loccount_perclass_persymframe[frame].items():
            classcounts[cls]['train'] += count
    for frame in val_frames:
        frame = os.path.basename(frame)
        #print(frame, list(loccount_perclass_persymframe[frame]))
        for cls,count in loccount_perclass_persymframe[frame].items():
            classcounts[cls]['val'] += count
    print('\n'.join(args.classes))
    pprint(classcounts)
    for cls in args.classes:
        dct = classcounts[cls]
        dct['total'] = dct['train'] + dct['val']
        dct['train_ratio'] = dct['train'] / dct['total']
        print(f"  {cls:>20}: TRAIN:VAL { dct['train']}:{ dct['val']} ({dct['train_ratio']:.0%},{1-dct['train_ratio']:.0%}) Total: {dct['total']}")
    print(f"FRAMES: training: {len(train_frames)}, validation: {len(val_frames)}, total: {len(train_frames)+len(val_frames)}")
    #TODO compare tator_classes to --classlist
    
    #8 create yaml file input for yolo train.py
    print('Writing dataset.yaml file')
    dataset_yaml = os.path.join(args.datadir, 'dataset.yaml')
    make_dataset_yaml('../'+args.datadir, train_txt, val_txt, args.classes, output=dataset_yaml)
    args.data = dataset_yaml
    
    #9 run train.py
    print('\n======================\n')
    if not args.skip_training:
        yolov5_ultralytics.train.main(args)
    
    
    
    #9 report on training metrics
    



