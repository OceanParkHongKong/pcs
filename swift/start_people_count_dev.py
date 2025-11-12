from start_people_count_manager import start_people_count_system
import os
import shlex

# Read user pass from Environment Variable
env_vars = {
    "CC_PASS": os.getenv("PEOPLE_COUNT_CC_PASS"),
    "CROCO_PASS": os.getenv("PEOPLE_COUNT_CROCO_PASS")
}

# Base path for regression test videos
REGRESSION_TEST_VIDEOS_BASE = "/YourPathToVideosFolder/PeopleCountRegressionTestVideos"

# Different camera configuration for testing
cameras_config = [
    "https://github.com/username/repo/releases/download/video_COL_In_Cam1_2025-10-04_08-20-32_colleagues_only_NO_guest.mp4 crocoland COL_In_Cam1 '' ''",
   # f"{REGRESSION_TEST_VIDEOS_BASE}/WaterWorld/HorizonCove/video_HC_190_26_2025-05-03_20-27-29.mp4 ww_pool_1920 C-3026 '[(127,405),(6,893),(467,908),(881,933),(1248,860),(1306,886),(1417,846),(1421,794),(1812,585),(1897,515),(1874,466),(1572,387),(790,364)]' region",
    # f"http://localhost:3006/video_feed ww_pool_1920 C-2001 '[(9,282),(12,1076),(1909,1072),(1914,417),(1581,269),(737,219),(385,240),(387,213)]' region",
    

    #Cyclone Spin + Tropical Twist + Rainbow Rush 
    # f"{REGRESSION_TEST_VIDEOS_BASE}/WaterWorld/CycloneSpin_TropicalTwist/video_P1-Ride01_2025-08-30_13-40-33.mp4 ww_9in1_slides P1-Ride01 '[(323,119),(392,314),(558,311),(563,23)]|[(362,148),(432,293),(336,299),(286,153)]' border_plus 252,572,661,1229",
]

if __name__ == "__main__":
    start_people_count_system(cameras_config)