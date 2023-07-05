# DEFINE THINGS
LOCALIZATION_CSV=demodata/locs.csv
TRAIN_DATADIR=demodata/yolo_dir
TRAIN_OUTDIR=demodata/TRAINING_RESULTS
IMGSIZE=640

conda activate tator
#1) download csv localizations from tator, optionally download frames
python download_localizations.py --token sbatchelder.token -p1 -l1 -v2 --statetype 1 \
    --state-att Verified True --outfile "$LOCALIZATION_CSV" --frame-download-dir demodata/frames

#2) add full frame paths column, if needed

#3) convert to yolo format
python convert_localization_csv_to_yolo_training.py "$LOCALIZATION_CSV" "$TRAIN_DATADIR" --imgiomode move

#4) run yolo train
conda deactivate
conda activate yolov5
cd yolov5
python train.py --data "../$TRAIN_DATADIR/dataset.yaml" --imgsz $IMGSIZE \
  --project "../$(dirname $TRAIN_OUTDIR)" --name "$(basename $TRAIN_OUTDIR)" --exist-ok \
  --epochs 200 --patience 50 --device 0 --weights yolov5s.pt --image-weights --optimizer Adam

#5) run yolo detect on validation data
python detect.py \
  --weights "../$TRAIN_OUTDIR/weights/best.pt" \
  --source "../$TRAIN_DATADIR/val.txt" \
  --project "../$(dirname $TRAIN_OUTDIR)" \
  --name "$(basename $TRAIN_OUTDIR)" --exist-ok \
  --imgsz $IMGSIZE \
  --conf-thres 0.45 \
  --iou-thres 0.25 \
  --save-txt --save-conf \
  --device 0  #cuda

#6) convert yolo detect result to csv
conda deactivate
conda activate tator
cd ..
python convert_yolo_labels_to_localization_csv.py $TRAIN_OUTDIR/labels --classfile $TRAIN_DATADIR/dataset.yaml $TRAIN_OUTDIR/val_results.csv

#7) upload yolo detect csv results to tator
python upload_localizations.py $TRAIN_OUTDIR/val_results.csv --token sbatchelder.token -p1 -l1 \
  --version "$(basename $TRAIN_OUTDIR)" \
  --force_version "conf-thres:0.45 iou-thres:0.25 imgsz:$IMGSIZE"