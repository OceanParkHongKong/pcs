source /System/Volumes/Data/Users/username/miniconda3/etc/profile.d/conda.sh
conda activate pcs

./start_people_count_reboot_daily.sh &

./start_people_count.sh &

#Mac Studio special, may need to change the path
# cd filebeat
# ./filebeat &
# cd ..

sudo gunicorn -b 0.0.0.0:4999 ../people_count_crocoland/mac_gpu_info:app 
#can not start mac_gpu_info? using python mac_gpu_info.py?