from start_people_count_manager import start_people_count_system
import os

# Read user pass from Environment Variable
env_vars = {
    "PASSO": os.getenv("PASSO")
}

# Different camera configuration for testing
cameras_config = [
    # Cyclone Spin & Tropical Twist
    f"rtsp://username1:{env_vars['PASSO']}@192.168.camera.ip1:554/axis-media/media.amp?fps=15 ww_9in1_slides P1-Ride01 '[(323,119),(392,314),(558,311),(563,23)]|[(362,148),(432,293),(336,299),(286,153)]' border_plus 252,572,661,1229",

    # Rainbow Rush
    f"rtsp://username3:{env_vars['PASSO']}@192.168.camera.ip3:554/axis-media/media.amp?fps=15 ww_9in1_slides P2-Ride03 '[(54,303),(970,363),(1132,172),(1134,7),(503,6),(259,127)]|[(107,290),(889,332),(861,365),(73,326)]' border_plus 59,699,611,1748",  
    
    # Cavern & Vortex
    f"rtsp://username4:{env_vars['PASSO']}@192.168.camera.ip4:554/axis-media/media.amp?fps=15 ww_9in1_slides C-2045 '[(409,248),(563,252),(566,61),(462,56),(410,118)]|[(421,127),(420,245),(395,245),(395,123)]' border_plus 60,380,676,1244",
]

if __name__ == "__main__":
    start_people_count_system(cameras_config)