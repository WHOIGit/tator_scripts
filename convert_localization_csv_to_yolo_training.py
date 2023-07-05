import argparse
import os
import random
from collections import defaultdict
import shutil

import pandas as pd
import yaml

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', metavar='CSV')
    parser.add_argument('outdir', metavar='YOLO_TRAINING_DIR')
    parser.add_argument('--classes', default='auto')
    parser.add_argument('--training-split', default=0.8, type=float)
    parser.add_argument('--clobber', action='store_true')
    parser.add_argument('--imgiomode', default='symlink', choices=('symlink','copy','move'))
    parser.add_argument('--col_x', default='x')
    parser.add_argument('--col_y', default='y')
    parser.add_argument('--col_w', default='width')
    parser.add_argument('--col_h', default='height')
    parser.add_argument('--col_class', default='Class')
    parser.add_argument('--col_imagepath', default='imagepath')
    parser.add_argument('--yamlfile', default='dataset.yaml')
    parser.add_argument('--imglistfile-train', default='train.txt')
    parser.add_argument('--imglistfile-val', default='val.txt')
    args = parser.parse_args()

    if os.path.isfile(args.classes):
        with open(args.classes) as f:
            args.classes = f.read().splitlines()

    return args


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


def trainval_split(frames:list, training_ratio:float):
    training_frames_total = round(training_ratio*len(frames))
    shuffled_frames = frames[:]
    random.shuffle(shuffled_frames)
    return shuffled_frames[:training_frames_total], shuffled_frames[training_frames_total:]


def localization_csv_to_dicts(args):
    dtypes = {args.col_x: float, args.col_y: float,
              args.col_w: float, args.col_h: float}
    df = pd.read_csv(args.src, dtype=dtypes)
    export_cols = [args.col_x, args.col_y, args.col_w, args.col_h,
                   args.col_class, args.col_imagepath]
    dicts = list(df[export_cols].T.to_dict().values())
    return dicts


def localizations_to_yolo_training_directories(args, localizations):

    # 1 check all frames are accessible on disk and group to tiff_frames
    print('Checking for Frames on-disk')
    missing_tiffs = []
    locs_per_frame = defaultdict(list)
    csv_classes = set()
    for l in localizations:
        if not os.path.isfile(l[args.col_imagepath]):
            missing_tiffs.append(l)
        realpath = os.path.realpath(l[args.col_imagepath])
        locs_per_frame[realpath].append(l)
        csv_classes.add(l[args.col_class])
    error_str = "Can't find tiff frames:\n  " + '  \n'.join([l[args.col_imagepath] for l in missing_tiffs])
    assert not missing_tiffs, error_str

    # 2 create outdir
    print(f'Setting up outdir: {args.outdir}')
    if os.path.isdir(args.outdir) and args.clobber:
        shutil.rmtree(args.outdir)
    os.makedirs(args.outdir)

    images_dir = os.path.join(args.outdir, 'images')
    labels_dir = os.path.join(args.outdir, 'labels')
    os.mkdir(images_dir)
    os.mkdir(labels_dir)

    # 3 create dst from frames on disk to outdir:/images
    loccount_perclass_perframe = defaultdict(lambda: defaultdict(int))  # d[framefile_n][classlabel_x]=0
    csv_classes = sorted(csv_classes)
    if args.classes == 'auto':
        args.classes = csv_classes
    # TODO else: check for incongruence

    dst_frames = []
    for realpath, localizations in locs_per_frame.items():
        frame_filename = os.path.basename(realpath)
        dst_frame = os.path.join(images_dir, frame_filename)
        if args.imgiomode == 'copy':
            shutil.copyfile(realpath, dst_frame)
        elif args.imgiomode == 'move':
            shutil.move(realpath, dst_frame)
        else:
            os.symlink(realpath, dst_frame)
        dst_frames.append(dst_frame)

        # 4 create label files on outdir:/labels for localizations for all frames
        # format: class x_center y_center width height
        label_filename = os.path.splitext(frame_filename)[0] + '.txt'
        label_file = os.path.join(labels_dir, label_filename)
        with open(label_file, 'w') as f:
            for l in localizations:
                class_idx = args.classes.index(l[args.col_class])
                # TODO xywh convert as needed
                center_x = l[args.col_x] + l[args.col_w] / 2
                center_y = l[args.col_y] + l[args.col_h] / 2
                f.write(f"{class_idx} {center_x} {center_y} {l[args.col_w]} {l[args.col_h]}\n")
                loccount_perclass_perframe[frame_filename][l[args.col_class]] += 1

    # 5 split frames into train and val lists, create train.txt and val.txt respectively
    print('Distributing Frames to Training and Validation datasets')
    # TODO split frames PERCLASS somehow
    # TODO check for class mismatches between tator locs and args.classes
    if not args.outdir.startswith('/'):
        cwd = os.getcwd()
        dst_frames = [os.path.join(cwd, frame) for frame in dst_frames]
    train_frames, val_frames = trainval_split(dst_frames, args.training_split)
    train_file = os.path.join(args.outdir, args.imglistfile_train)
    val_file = os.path.join(args.outdir, args.imglistfile_val)
    with open(train_file, 'w') as f:
        f.write('\n'.join(train_frames))
    with open(val_file, 'w') as f:
        f.write('\n'.join(val_frames))

    # 6 report metrics
    classcounts = defaultdict(lambda: defaultdict(int))
    print('CLASSES:')
    for frame in train_frames:
        frame = os.path.basename(frame)
        for cls, count in loccount_perclass_perframe[frame].items():
            classcounts[cls]['train'] += count
    for frame in val_frames:
        frame = os.path.basename(frame)
        for cls, count in loccount_perclass_perframe[frame].items():
            classcounts[cls]['val'] += count
    for cls in args.classes:
        dct = classcounts[cls]
        dct['total'] = dct['train'] + dct['val']
        dct['train_ratio'] = dct['train'] / dct['total']
        print(
            f"  {cls:>20}: TRAIN:VAL {dct['train']}:{dct['val']} ({dct['train_ratio']:.0%},{1 - dct['train_ratio']:.0%}) Total: {dct['total']}")
    print(
        f"FRAMES: training: {len(train_frames)}, validation: {len(val_frames)}, total: {len(train_frames) + len(val_frames)}")
    # TODO compare tator_classes to --classlist

    # 7 create yaml file input for yolo train.py
    print(f'Writing {args.yamlfile} file')
    dataset_yaml = os.path.join(args.outdir, args.yamlfile)
    make_dataset_yaml(args.outdir if args.outdir.startswith('/') else '../' + args.outdir,
                      args.imglistfile_train, args.imglistfile_val, args.classes, output=dataset_yaml)
    args.data = dataset_yaml


if __name__=='__main__':
    args = cli()
    localizations = localization_csv_to_dicts(args)
    print(localizations)
    localizations_to_yolo_training_directories(args, localizations)