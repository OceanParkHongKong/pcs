#source /System/Volumes/Data/Users/username/miniconda3/etc/profile.d/conda.sh
source /System/Volumes/Data/opt/anaconda3/etc/profile.d/conda.sh
conda activate pcs

./start_people_count_reboot_daily_ww.sh &

./start_people_count_ww.sh &
