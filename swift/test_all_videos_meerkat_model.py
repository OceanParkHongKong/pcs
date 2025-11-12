import subprocess
import datetime
import atexit


video_files = [
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_14-29-52.mp4", '', 0, 54),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_14-39-54.mp4", '', 0, 14),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_14-49-56.mp4", '', 0, 24),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_14-59-57.mp4", '', 0, 23),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_17-50-30.mp4", '', 0, 58),
    ("/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/PeopleCountGA_MEK_AIA_NP_Verify/video_MEK_Out_Cam1_2024-08-12_18-50-39.mp4", '', 0, 13),
]

import test_all_videos_crocoland

redis_key_1 = "Meerkat"
model_name_1 = "meerkat"
result_file_1 = "test_result_meerkat_model.txt"


# Run tests for the first set of video files
test_all_videos_crocoland.run_tests(video_files, redis_key_1, model_name_1, result_file_1, parallel=10)

