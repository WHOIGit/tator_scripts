#!/usr/bin/env bash
#SBATCH --job-name=video2tator
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=1GB
#SBATCH --time=6:00:00
#SBATCH --mail-type=ALL
#SBATCH --mail-user=
#SBATCH --partition=compute
#SBATCH --output=slogs/video2tator/%j.%x.txt

# LOGGING JOB DETAILS #
echo "Job ID: $SLURM_JOB_ID, JobName: $SLURM_JOB_NAME"
hostname; pwd; date

# SETTING UP ENVIRONMENT #
module purge
module load ffmpeg
module load gcc/8.5.0
source _tator_/bin/activate
umask 000  # newly created files have all-open permissions ok. 

echo "Environment... loaded"

set -eux  # exit on error, including unset vars

# Get target dir to from list and slurm-array-index to convert to video
VIDEO_FILE="$1"
VIDEO_NAME=$(basename "${VIDEO_FILE%.*}")

## TRANSCODING AND UPLOADING TO TATOR ##

echo "TATOR-PY..."
TOKEN=$(cat cloud.token)  # hpc-user access token
HOST=https://cloud.tator.io
PROJ_ID=219   # WHOI Test
MEDIA_ID=548  # shadowgraph video

time python3 -m tator.transcode "$VIDEO_FILE" \
    --name "$VIDEO_NAME" \
    --host "$HOST" \
    --token "$TOKEN" \
    --project $PROJ_ID \
    --type $MEDIA_ID \
    --section testset \
    --work_dir "tator_transcode_workspace" \
    --hwaccel

echo 
TZ=UTC0 printf '%(%H:%M:%S)T\n' $SECONDS


