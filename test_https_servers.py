import os

import numpy as np
import time
import pytest

import argparse

from requests.exceptions import MissingSchema
from activestorage.active import Active, load_from_https

S3_BUCKET = "bnl"
def test_https():
    """
    Run a https test with a small enough file for the test
    not to be marked as slow. We test all aspects here.
    File: https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-1-LL/piControl/r1i1p1f2/Amon/ta/gn/latest/ta_Amon_UKESM1-1-LL_piControl_r1i1p1f2_gn_274301-274912.nc
    Size: 75 MiB, variable: ta
    Entire test uses at most 400M RES memory.
    """
   
    global np
   

    test_file_uri = "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-1-LL/piControl/r1i1p1f2/Amon/ta/gn/latest/ta_Amon_UKESM1-1-LL_piControl_r1i1p1f2_gn_274301-274912.nc"
    #test_file_uri = "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/AerChemMIP/MOHC/UKESM1-0-LL/ssp370SST-lowNTCF/r1i1p1f2/Amon/cl/gn/v20200420/cl_Amon_UKESM1-0-LL_ssp370SST-lowNTCF_r1i1p1f2_gn_205001-209912.nc"
    #GWS File
    #test_file_uri = "https://gws-access.jasmin.ac.uk/public/ukesm/TerraFIRMA/esm-piControl/r1i1p1f1/Amon/ta/gn/v20241002/ta_Amon_UKESM1-2-LL_esm-piControl_r1i1p1f1_gn_210001-214912.nc"

    myVar = "ta"
    #myVar = "cl"
    active_storage_url = "https://reductionist.jasmin.ac.uk/"  # Wacasoft new Reductionist

    # v1: all local
    active = Active(test_file_uri, myVar)
    active._version = 1
    result = active.min()[0:3, 4:6, 7:9]
    print("Result is", result)
    result == np.array([220.3180694580078], dtype="float32")
    print("Check: ", result )

    #assert result == np.array([220.3180694580078], dtype="float32")


    # v2: declared storage type, no activa storage URL
    active = Active(test_file_uri, myVar,
                    interface_type="https", )
    active._version = 1
    with pytest.raises(MissingSchema):
        result = active.min()[0:3, 4:6, 7:9]

    # v2: declared storage type
    active = Active(test_file_uri,myVar,
                    interface_type="https",
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)
    active._version = 2
    result = active.min()[0:3, 4:6, 7:9]
    print("Result is", result)
    #assert result == np.array([220.3180694580078], dtype="float32")

    # v2: inferred storage type
    active = Active(test_file_uri, myVar,
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)
    active._version = 2
    result = active.min()[0:3, 4:6, 7:9]
    print("Result is", result)
    #assert result == np.array([220.3180694580078], dtype="float32")

    # set these as fixed floats
    f_1 = 176.882080078125
    f_2 = 190.227783203125

    
    
    # v2: inferred storage type, pop axis
    active = Active(test_file_uri, myVar,
                    interface_type="https",
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)

    active._version = 2
    #result = active.min(axis=(0, 1))[:]

    all_mins = []
    for i in range(0, 84, 4): 
        chunk_min = active[i : i+4, :, :, :].min(axis=(0, 1))[:]
        all_mins.append(chunk_min)

    result = np.min(all_mins, axis=0)

    print("Result is", result)
    print("Result shape is", result.shape)

    print(result[0, 0])
    print(result[143, 191])
    
    #assert result.shape == (1, 1, 144, 192)
    #assert result.shape == (144, 192)
    
    #assert result[0, 0] == f_1
    #assert result[143, 191] == f_2
    
    # load dataset with Pyfive
    dataset = load_from_https(test_file_uri)
    av = dataset[myVar]
    r_min = np.min(av[:], axis=(0, 1))
    # NOTE the difference in shapes:
    # - Reductionist: (1, 1, 144, 192)
    # - numpy: (144, 192)
    # Contents is identical though.
    print(r_min)
    #assert r_min[0, 0] == f_1
    #assert r_min[143, 191] == f_2

    # basic auth on; username and password
    # should work with both Active and Reductionist but we
    # don't have such an NGINX-auth-ed file yet
    active = Active(test_file_uri, myVar,
                    interface_type="https",
                    storage_options={"username": None, "password": None},
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)

    active._version = 2

    #result = active.min(axis=(0, 1))[:]

    all_mins = []
    for i in range(0, 84, 4):  # Process 10 months at a time
        chunk_min = active[i : i+4, :, :, :].min(axis=(0, 1))[:]
        all_mins.append(chunk_min)

    # Then find the global min from your results
    import numpy as np
    result = np.min(all_mins, axis=0)

    print("Result is", result)
    print("Result shape is", result.shape)
    #assert result.shape == (144, 192)
    #assert result[0, 0] == f_1
    #assert result[143, 191] == f_2

    # run with pyfive.Dataset instead of File
    dataset = load_from_https(test_file_uri)
    av = dataset[myVar]
    active = Active(av,
                    active_storage_url=active_storage_url)
    active._version = 2
    print("Interface type", active.interface_type)
    result = active.min(axis=(0, 1))[:]
    print("Result is", result)
    print("Result shape is", result.shape)
    #assert result.shape == (1,1, 144, 192)
    #assert result[0,0,0, 0] == f_1
    #assert result[0,0,143, 191] == f_2
    

def test_https_stresstest():
    test_file_uri = "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-1-LL/piControl/r1i1p1f2/Amon/ta/gn/latest/ta_Amon_UKESM1-1-LL_piControl_r1i1p1f2_gn_274301-274912.nc"
    myVar = "ta"
    active_storage_url = "https://reductionist.jasmin.ac.uk/" 

    f_1 = 176.882080078125
    f_2 = 190.227783203125

    active = Active(test_file_uri, myVar,
                    interface_type="https",
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)
    active._version = 2

    # --- STEP 1: Find the Reductionist Limit (Stress Test) ---
    print("Finding server-side limit...")
    safe_limit = 5  # Default fallback
    #(84, 19, 144, 192)
    for size in range(1, 84, 1):  # Test 10, 20, 30...
        try:
            start = time.time()
            # Probe: Just fetch a slice to see if the server chokes
            #_ = active[0:size, :, :, :].min(axis=(0, 1))[:]
            _ = active[0:size, :, :, :].min()
            print(f"  SUCCESS: Server handled {size} time-steps in {time.time()-start:.2f}s")
            safe_limit = size
        except Exception as e:
            print(f"  FAILED: Server reached limit at {size} steps. Error: {e}")
            break

    print(f"Proceeding with chunk size: {safe_limit}")

    # --- STEP 2: Use the discovered limit to process the whole file ---
    all_mins = []
    total_steps =  84 #in this case

    for i in range(0, total_steps, safe_limit):
        # Ensure we don't go out of bounds on the final slice
        end = min(i + safe_limit, total_steps)
        chunk_min = active[i:end, :, :, :].min()[:]
        #chunk_min = active[i:end, :, :, :].min(axis=(0, 1))[:]
        all_mins.append(chunk_min)

    # Combine results
    result = np.min(all_mins, axis=0)

    # --- STEP 3: Assertions ---
    print("Final Result shape:", result.shape)
    #assert result.shape == (144, 192)
    
    # Use np.isclose for floating point safety
    #assert np.isclose(result[0, 0], f_1)
    #assert np.isclose(result[143, 191], f_2)
    print("Stress test and validation passed!")

def test_response_https(nChunks):
    """
    Run a https test with a small enough file for the test
    """
   
    global np
    print("----------------------------------------------------------------------")
    print("https Response")
    print("----------------------------------------------------------------------")

    #MY TEST FILE
    #test_file_uri = "https://gws-access.jasmin.ac.uk/public/canari/varsiha/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc"
    #myVar="clw"

    #test_file_uri = "https://gws-access.jasmin.ac.uk/public/canari/varsiha/tas_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc"	
    #myVar="tas"

    test_file_uri = "https://gws-access.jasmin.ac.uk/public/canari/varsiha/ch330a.pc19790301-def.nc"
    myVar="UM_m01s16i202_vn1106"

    #test_file_uri = "http://esgf3.dkrz.de/thredds/fileServer/cmip6/RFMIP/MPI-M/MPI-ESM1-2-LR/piClim-spAer-anthro/r1i1p1f2/Amon/tas/gn/v20190710/tas_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc"
    #myVar="tas"

    #File:           ch330a.pc19790301-def.nc
    #Dataset:        UM_m01s16i202_vn1106              
    #Shape:          (40, 1920, 2560)                             
    #Chunks per axis [4, 4, 4]                                    
    #Chunks          64                                           
    
    #myVar="clw"
    active_storage_url = "https://reductionist.jasmin.ac.uk/"  # Wacasoft new Reductionist

    # set these as fixed floats
    f_1 = 176.882080078125
    f_2 = 190.227783203125

    # v2: inferred storage type, pop axis
    active = Active(test_file_uri, myVar,
                    interface_type="https",
                    active_storage_url=active_storage_url,
                    option_disable_chunk_cache=True)

    active._version = 1

    #Chunk Size 10, 480, 640
    #Shape:          (40, 1920, 2560)                             
    #Chunks per axis [4, 4, 4]                                    
    #Chunks          64    
    
    result = active.min(axis=(0,1))[0: nChunks[0]*10,0:nChunks[1]*480, 0:nChunks[2]*640]
    
    print("Result is", result)
    print("Result shape is", result.shape)

  
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="To add parser options for LOTUS Batch submission"
    )

    parser.add_argument(
        "--nChunks",
        nargs=3,          # exactly 3 values
        type=int,         # convert them to integers
        help="Three chunk numbers"
    )

    args = parser.parse_args()

    print(args.nChunks)

    test_response_https(args.nChunks)