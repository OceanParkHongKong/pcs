from start_people_count_manager import start_people_count_system
import os
# Read user pass from Environment Variable
env_vars = {
    "CC_PASS": os.getenv("PEOPLE_COUNT_CC_PASS"),
    "CROCO_PASS": os.getenv("PEOPLE_COUNT_CROCO_PASS")
}

# List of commands to run
cameras_config = [
    f"http://{env_vars['CROCO_PASS']}@192.168.camera.ip5/mjpg/video.mjpg crocoland COL_In_Cam1 '' ''",
    f"http://{env_vars['CC_PASS']}@192.168.camera.ip8/mjpg/video.mjpg cableCar OE_Out_Cam4 '[(0,150),(640,150),(640,200),(0,200)]' ''",# higher region points to see more babies in cart  
    f"http://{env_vars['CC_PASS']}@192.168.camera.ip35/mjpg/video.mjpg cableCar ER_In_Cam1 '[(250,0),(250,640),(300,640),(300,0)]' 'x-'",    
    # "/Users/SomeBody/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountCrocoland/video_2024-03-22_09-28-26.mp4 crocoland COL_In_Cam1 '' ''",
]

if __name__ == "__main__":
    start_people_count_system(cameras_config)