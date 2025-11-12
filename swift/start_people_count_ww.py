from start_people_count_manager import start_people_count_system
import os

# Read user pass from Environment Variable
env_vars = {
    "PASSO": os.getenv("PASSO")
}

# Different camera configuration for testing
cameras_config = [
    # BigWaveBay
    f"rtsp://username1:{env_vars['PASSO']}@192.168.camera.ip1:554/axis-media/media.amp?fps=15 ww_pool_1920 C-2001 '[(10,1072),(1908,459),(1912,402),(1562,259),(963,212),(400,231),(396,205),(4,266)]' region",
    # RipTide
    f"rtsp://username8:{env_vars['PASSO']}@192.168.camera.ip8:554/axis-media/media.amp?fps=15 ww_riptide C-2088 '[(637,128),(489,114),(319,101),(54,110),(5,140),(16,200),(156,308),(384,427),(636,546)]|[(160,279),(151,331),(636,578),(639,508)]' border_plus_reverse 202,842,1279,1919",
    # LazyCruise
    f"rtsp://username11:{env_vars['PASSO']}@192.168.camera.ip11:554/axis-media/media.amp?fps=15 ww_riptide C-2058 '[(273,282),(281,312),(595,302),(589,266)]' y+ 367,1007,832,1472",

]

if __name__ == "__main__":
    start_people_count_system(cameras_config)