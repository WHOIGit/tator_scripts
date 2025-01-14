#!/usr/bin/env bash
#SBATCH --job-name=locs2tator
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=2GB
#SBATCH --time=6:00:00
#SBATCH --partition=compute
#SBATCH --mail-type=ALL
#SBATCH --mail-user=
#SBATCH --array=
#SBATCH --output=slogs/locs2tator/%A.%a.%x.txt

# LOGGING JOB DETAILS #
echo "Job ID: $SLURM_JOB_ID, JobName: $SLURM_JOB_NAME"
hostname; pwd; date

# SETTING UP ENVIRONMENT #
module load python3/3.9.10
source _tator_/bin/activate
echo "Environment... loaded"

set -eux  # exit on error, including unset vars

# Get target dir to from list and slurm-array-index to convert to video
CSVs_LIST="$1"
CSV_FILE=$(sed "${SLURM_ARRAY_TASK_ID}q;d" $CSVs_LIST)


## UPLOADING TO TATOR ##

TOKEN=$(cat sbatchelder.token)  # hpc-user access token
HOST=https://tator.whoi.edu
PROJ_ID=1   # ISIIS
LOCTYPE_ID=1  # ROI localization type
VERSION_ID=21  # exp435_img1280
MODEL_NAME="exp435_best/img-1280_iou-0.5_conf-0.5_agNMS-True"

# check classes
#CSV_FILE_CORRECTED=/tmp/$SLURM_JOB_NAME/$SLURM_JOB_ID/CORRECTED_CSV.${SLURM_ARRAY_TASK_ID}.csv
python3 csv_util.py "$CSV_FILE" --action check_classes -p $PROJ_ID --token $TOKEN 
# will error if check fails. 

time python3 upload_localizations.py "$CSV_FILE" --token $TOKEN -p $PROJ_ID -l $LOCTYPE_ID -v $VERSION_ID --col-drop class_idx --col-rename score ModelScore --col-add ModelName $MODEL_NAME

echo 
TZ=UTC0 printf '%(%H:%M:%S)T\n' $SECONDS



