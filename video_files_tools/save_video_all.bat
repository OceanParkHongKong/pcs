@echo off

REM Set the environment variables
set "PEOPLE_COUNT_CC_PASS=username:password"
set "PEOPLE_COUNT_CROCO_PASS=username:password"

REM Define the URL and camera name pairs, and start the video capture command

REM Camera 1
set "URL1=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip1/mjpg/video.mjpg"
set "CAM1=CC_In_Cam1"
start "" python save_video.py --url "%URL1%" --camera_name "%CAM1%" >> "%CAM1%_output_log.txt" 2>&1

REM Camera 2
set "URL2=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip2/mjpg/video.mjpg"
set "CAM2=CC_In_Cam2"
start "" python save_video.py --url "%URL2%" --camera_name "%CAM2%" >> "%CAM2%_output_log.txt" 2>&1

REM Camera 3
set "URL3=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip3/mjpg/video.mjpg"
set "CAM3=CC_Out_Cam1"
start "" python save_video.py --url "%URL3%" --camera_name "%CAM3%" >> "%CAM3%_output_log.txt" 2>&1

REM Camera 4
set "URL4=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip4/mjpg/video.mjpg"
set "CAM4=CC_Out_Cam2"
start "" python save_video.py --url "%URL4%" --camera_name "%CAM4%" >> "%CAM4%_output_log.txt" 2>&1

REM Camera 5
set "URL5=http://%PEOPLE_COUNT_CROCO_PASS%@192.168.camera.ip5/mjpg/video.mjpg"
set "CAM5=COL_In_Cam1"
start "" python save_video.py --url "%URL5%" --camera_name "%CAM5%" >> "%CAM5%_output_log.txt" 2>&1

REM Camera 6
set "URL6=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip6/mjpg/video.mjpg"
set "CAM6=OE_Out_Cam2"
start "" python save_video.py --url "%URL6%" --camera_name "%CAM6%" >> "%CAM6%_output_log.txt" 2>&1

REM Uncomment the following lines if needed

REM Camera 7
set "URL7=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip7/mjpg/video.mjpg"
set "CAM7=OE_Out_Cam3"
start "" python save_video.py --url "%URL7%" --camera_name "%CAM7%" >> "%CAM7%_output_log.txt" 2>&1

REM Camera 8
set "URL8=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip8/mjpg/video.mjpg"
set "CAM8=OE_Out_Cam4"
start "" python save_video.py --url "%URL8%" --camera_name "%CAM8%" >> "%CAM8%_output_log.txt" 2>&1

REM Camera 9
set "URL9=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip9/mjpg/video.mjpg"
set "CAM9=OE_Out_Cam5"
start "" python save_video.py --url "%URL9%" --camera_name "%CAM9%" >> "%CAM9%_output_log.txt" 2>&1

REM Camera 10
set "URL10=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip10/mjpg/video.mjpg"
set "CAM10=OE_Out_Cam6"
start "" python save_video.py --url "%URL10%" --camera_name "%CAM10%" >> "%CAM10%_output_log.txt" 2>&1

REM Camera 11
set "URL11=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip11/mjpg/video.mjpg"
set "CAM11=OE_In_Cam1"
start "" python save_video.py --url "%URL11%" --camera_name "%CAM11%" >> "%CAM11%_output_log.txt" 2>&1

REM Camera 12
set "URL12=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip12/mjpg/video.mjpg"
set "CAM12=OE_In_Cam2"
start "" python save_video.py --url "%URL12%" --camera_name "%CAM12%" >> "%CAM12%_output_log.txt" 2>&1

REM Camera 13
set "URL13=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip13/mjpg/video.mjpg"
set "CAM13=OE_In_Cam3"
start "" python save_video.py --url "%URL13%" --camera_name "%CAM13%" >> "%CAM13%_output_log.txt" 2>&1

REM Camera 14
set "URL14=http://%PEOPLE_COUNT_CC_PASS%@192.168.camera.ip14/mjpg/video.mjpg"
set "CAM14=OE_In_Cam4"
start "" python save_video.py --url "%URL14%" --camera_name "%CAM14%" >> "%CAM14%_output_log.txt" 2>&1