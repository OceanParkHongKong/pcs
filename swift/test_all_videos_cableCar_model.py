# Define the base path as a configurable variable
base_path = "/Users/username/Library/CloudStorage/OneDrive-OceanParkCorporation/PeopleCountRegressionTestVideos/"

video_files_deskside = [
    #Cable car
    (f"{base_path}PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-13-30.mp4", "", 18, 0), 
    (f"{base_path}PeopleCountCableCar/CableCarUp/video_CC_In_Cam1_2024-07-01_11-33-41.mp4", "", 129, 0), 
    (f"{base_path}PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-03-25.mp4", "", 83, 0), 
    (f"{base_path}PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_11-53-52.mp4", "", 136, 0), 
    (f"{base_path}PeopleCountCableCar/CableCarUp/video_CC_In_Cam2_2024-07-01_18-32-12.mp4", "", 16, 0), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_12-58-24.mp4", "", 0, 84), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_13-18-29.mp4", "", 0, 63), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam1_2024-07-01_18-09-39.mp4", "", 0, 123), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_13-37-23.mp4", "", 12, 14), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-09-18.mp4", "", 0, 114), 
    (f"{base_path}PeopleCountCableCar/CableCarDown/video_CC_Out_Cam2_2024-07-01_18-59-36.mp4", "", 0, 122), 
    
    #Ocean Express (updated with expected in values)
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_10-18-09.mp4", "", 31, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam1_2024-06-24_10-28-14.mp4", "", 63, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam2_2024-07-08_13-02-43.mp4", "", 52, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_11-28-19.mp4", "", 240, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam3_2024-06-23_11-38-25.mp4", "", 323, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam4_2024-06-19_10-01-40.mp4", "", 143, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_In_Cam4_2024-06-19_10-11-44.mp4", "", 417, 0),
    (f"{base_path}PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-02-18.mp4", "", 0, 97),
    (f"{base_path}PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-12-23.mp4", "", 0, 79),
    (f"{base_path}PeopleCountOceanExpress/video_OE_Out_Cam4_2024-06-23_17-32-32.mp4", "", 0, 130),
    (f"{base_path}PeopleCountOceanExpress/video_OE_Out_Cam5_2024-06-19_12-12-45.mp4", "", 0, 178),
    (f"{base_path}PeopleCountOceanExpress/video_OE_Out_Cam6_2024-06-22_17-06-04.mp4", "", 0, 22), 
    
    #Sloth and friends
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam1_2024-08-12_12-39-35.mp4", "", 42, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam1_2024-08-12_13-09-40.mp4", "", 46, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam1_2024-08-12_14-59-58.mp4", "", 53, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam2_2024-08-10_14-42-46.mp4", "", 0, 61),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam2_2024-08-11_14-56-18.mp4", "", 0, 70),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_AIA_In_Cam2_2024-08-12_15-20-01.mp4", "", 0, 86),
    
    #Grand Aquarium (updated with expected in and out values)
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_In_Cam1_2024-08-12_10-39-17.mp4", "", 44, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_In_Cam1_2024-08-12_11-39-26.mp4", "", 205, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_In_Cam1_2024-08-12_17-00-19.mp4", "", 155, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_Out_Cam1_2024-08-12_14-29-53.mp4", "", 0, 123),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_Out_Cam1_2024-08-12_17-30-25.mp4", "", 0, 134),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_GA_Out_Cam1_2024-08-13_11-03-43.mp4", "", 0, 153),
    
    #North Pole (updated with expected in and out values)
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_In_Cam1_2024-08-11_12-56-00.mp4", "", 216, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_In_Cam1_2024-08-11_13-06-01.mp4", "", 229, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_In_Cam1_2024-08-11_18-26-47.mp4", "", 16, 0),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_Out_Cam1_2024-08-08_16-28-28.mp4", "", 11, 193),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_Out_Cam1_2024-08-08_16-38-30.mp4", "", 9, 147),
    (f"{base_path}PeopleCountGA_MEK_AIA_NP_Verify/video_NP_Out_Cam1_2024-08-08_18-06-28.mp4", "", 1, 49),
    
    #SP South Pole
    (f"{base_path}PeopleCountSouthPole/video_SP_In_Cam1_2024-08-22_13-03-49.mp4", "", 231, 7),
    (f"{base_path}PeopleCountSouthPole/video_SP_In_Cam1_2024-08-22_13-13-51.mp4", "", 170, 2),
    (f"{base_path}PeopleCountSouthPole/video_SP_In_Cam1_2024-08-22_13-23-53.mp4", "", 174, 4),
    (f"{base_path}PeopleCountSouthPole/video_SP_Out_Cam1_2024-08-22_13-03-47.mp4", "", 6, 238),
    (f"{base_path}PeopleCountSouthPole/video_SP_Out_Cam1_2024-08-22_13-13-49.mp4", "", 5, 178),
    (f"{base_path}PeopleCountSouthPole/video_SP_Out_Cam1_2024-08-22_13-23-51.mp4", "", 2, 218),
    
    #AAA Amazing Asian Animals (updated with expected in/out values)
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_In_Cam1_2024-08-09_15-04-00.mp4", "", 124, 4),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_In_Cam1_2024-08-10_10-36-45.mp4", "", 60, 8),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_In_Cam1_2024-08-11_16-31-05.mp4", "", 169, 11),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam1_2024-08-11_15-20-53.mp4", "", 2, 27),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam1_2024-08-26_17-18-13.mp4", "", 19, 11),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam1_2024-08-26_14-46-38.mp4", "", 9, 4),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam2_2024-08-09_14-52-43.mp4", "", 2, 161),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam2_2024-08-09_17-03-01.mp4", "", 4, 144),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/old/video_AAA_Out_Cam2_2024-08-10_19-06-54.mp4", "", 0, 21),
    
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam1_2025-02-10_17-42-01.mp4", "[(11,299),(10,347),(267,352),(560,106),(514,84),(258,296)]", 82, 89),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam1_2025-02-10_17-52-03.mp4", "[(11,299),(10,347),(267,352),(560,106),(514,84),(258,296)]", 38, 48),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam1_2025-02-13_14-21-39.mp4", "[(11,299),(10,347),(267,352),(560,106),(514,84),(258,296)]", 116, 127),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2025-02-10_17-32-11.mp4", "[(16,226),(15,284),(422,279),(590,79),(550,44),(403,217)]", 89, 75),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2025-02-10_17-42-12.mp4", "[(16,226),(15,284),(422,279),(590,79),(550,44),(403,217)]", 78, 91),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_Out_Cam2_2025-02-13_14-31-33.mp4", "[(16,226),(15,284),(422,279),(590,79),(550,44),(403,217)]", 145, 80),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_In_Cam1_2025-02-12_11-10-47.mp4", "", 225, 4),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_In_Cam1_2025-02-12_11-20-48.mp4", "", 229, 8),
    (f"{base_path}PeopleCountAmazingAsiaAnimals/video_AAA_In_Cam1_2025-02-12_11-30-49.mp4", "", 292, 0),
    
    
    #SJS JellyFish (updated with expected in/out values)
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_In_Cam1_2024-08-23_14-29-54.mp4", "", 81, 4),
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_In_Cam1_2024-08-25_14-16-09.mp4", "", 67, 5),
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_In_Cam1_2024-08-23_15-20-09.mp4", "", 35, 7),
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_Out_Cam1_2024-08-23_14-19-51.mp4", "", 28, 115),
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_Out_Cam1_2024-08-23_15-30-12.mp4", "", 12, 29),
    (f"{base_path}PeopleCountSJS_Jellyfish/video_SJS_Out_Cam1_2024-08-25_14-26-12.mp4", "", 9, 125),
    
    #SM Shark Mystique (updated with expected in/out values)
    (f"{base_path}PeopleCountSharkMuseum/video_SM_In_Cam1_2024-08-22_14-23-55.mp4", "", 213, 8),
    (f"{base_path}PeopleCountSharkMuseum/video_SM_In_Cam1_2024-08-22_15-14-02.mp4", "", 73, 7),
    (f"{base_path}PeopleCountSharkMuseum/video_SM_In_Cam1_2024-08-22_15-54-09.mp4", "", 259, 11),   
    (f"{base_path}PeopleCountSharkMuseum/video_SM_Out_Cam1_2024-08-22_14-04-01.mp4", "", 8, 138),   
    (f"{base_path}PeopleCountSharkMuseum/video_SM_Out_Cam1_2024-08-22_14-24-05.mp4", "", 5, 102),   
    (f"{base_path}PeopleCountSharkMuseum/video_SM_Out_Cam1_2024-08-22_15-54-23.mp4", "", 6, 117),   
    
    #Arctic Fox (updated with expected in/out values)
    (f"{base_path}PeopleCountArcticFox/video_AF_In_Cam1_2024-09-15_11-23-50_640_480.mp4", '[(0,150),(640,150),(640,200),(0,200)]', 46, 9),
    (f"{base_path}PeopleCountArcticFox/video_AF_In_Cam1_2024-09-15_16-34-48_640_480.mp4", '[(0,150),(640,150),(640,200),(0,200)]', 44, 17),
    (f"{base_path}PeopleCountArcticFox/video_AF_In_Cam1_2024-09-15_16-45-10_640_480.mp4", '[(0,150),(640,150),(640,200),(0,200)]', 59, 16),      

    #Explore R (updated with expected in/out values)
    (f"{base_path}PeopleCount_ST_ER/video_ER_Out_Cam2_2024-12-08_16-18-32.mp4", '[(0,250),(640,250),(640,300),(0,300)]', 39, 3),
    (f"{base_path}PeopleCount_ST_ER/video_ER_Out_Cam2_2024-12-08_16-28-33.mp4", '[(0,250),(640,250),(640,300),(0,300)]', 44, 1),      
    (f"{base_path}PeopleCount_ST_ER/video_ER_Out_Cam2_2024-12-08_16-38-34.mp4", '[(0,250),(640,250),(640,300),(0,300)]', 34, 2),
    
    #Sichuan Panda (updated with expected in/out values)
    (f"{base_path}PeopleCount_ST_ER/video_ST_In_Cam1_2024-12-09_10-51-20.mp4", '', 6, 37),  
    (f"{base_path}PeopleCount_ST_ER/video_ST_In_Cam1_2024-12-09_11-11-23.mp4", '', 4, 1),  
    (f"{base_path}PeopleCount_ST_ER/video_ST_In_Cam1_2024-12-09_11-21-24.mp4", '', 76, 10),  
    (f"{base_path}PeopleCount_ST_ER/video_ST_Out_Cam1_2024-12-09_10-51-20.mp4", '', 1, 34),  
    (f"{base_path}PeopleCount_ST_ER/video_ST_Out_Cam1_2024-12-09_11-11-23.mp4", '', 45, 0),  
    (f"{base_path}PeopleCount_ST_ER/video_ST_Out_Cam1_2024-12-09_11-21-24.mp4", '', 16, 48),  
    
    
    #PP (updated with expected in/out values)
    (f"{base_path}PeopleCountPP/video_PP_In_Cam1_2025-01-20_12-41-06.mp4", '', 49, 56),
    (f"{base_path}PeopleCountPP/video_PP_In_Cam1_2025-01-20_12-51-07.mp4", '', 60, 58),
    (f"{base_path}PeopleCountPP/video_PP_In_Cam1_2025-01-20_15-41-28.mp4", '', 15, 47),
    (f"{base_path}PeopleCountPP/video_PP_Out_Cam1_2025-01-06_14-31-11.mp4", '', 4, 6),
    (f"{base_path}PeopleCountPP/video_PP_Out_Cam1_2025-01-06_14-41-12.mp4", '', 2, 2),
    (f"{base_path}PeopleCountPP/video_PP_Out_Cam1_2025-01-07_14-41-29.mp4", '', 1, 18),
]

import test_all_videos_crocoland

redis_key_1 = "CC_In_Cam"
model_name_1 = "cableCar"
result_file_1 = "test_result_cablecar_model.txt"

# Run tests for the first set of video files
test_all_videos_crocoland.run_tests(video_files_deskside, redis_key_1, model_name_1, result_file_1, parallel=10)
