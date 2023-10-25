import argparse
import os
import pandas as pd


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', metavar='YOLO_LABELS_DIR')
    parser.add_argument('--classfile', required=True)
    parser.add_argument('outfile', metavar='CSV')
    args = parser.parse_args()

    return args

def do_it(src):
    locs = []
    # 1 go through files in labels dir
    for root, directories, files in os.walk(src):
         for filename in files:
             # 2 for each file determine the media and frame
             media = root.rstrip('/').replace('/labels','').split('/')[-1]
             basler_id,frame = os.path.splitext(filename)[0].rsplit('_',1)
             frame = int(frame)
             with open(os.path.join(root,filename)) as f:
                 for line in f.read().splitlines():
                     # 3 extract "class x y w h score" lines from file
                     c,x,y,w,h,s = line.strip().split()
                     c,x,y,w,h,s = int(c),float(x),float(y),float(w),float(h),float(s)
                     loc = dict(media=media, frame=frame,
                                x=x, y=y, width=w, height=h,
                                score=s, class_idx=c)
                     print(loc)
                     locs.append(loc)

    # 4 make a csv with pandas
    df = pd.DataFrame.from_records(locs)
    return df


if __name__=='__main__':
    args = cli()
    df = do_it(args.src)

    # 4 convert class idx to str (using yaml file?)
    with open(args.classfile) as f:
        if args.classfile.endswith('.yaml'):
            import yaml
            yaml_data = yaml.safe_load(f)
            classes = yaml_data['names']
        elif args.classfile.endswith('.pt'):
            from ultralytics import YOLO
            classes = list(YOLO(args.classfile).names.values())
        else:
            classes = f.read().splitlines()
    df['Class'] = df.class_idx.apply(lambda c: classes[c])

    df.sort_values(by=['media','frame', 'x', 'y'], inplace=True)
    df.to_csv(args.outfile, index=False)
