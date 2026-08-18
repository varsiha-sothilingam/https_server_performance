import concurrent.futures
import time
import numpy as np
import fsspec
import pyfive
from aiohttp import ClientResponseError # Import to catch the specific HTTP error
from datetime import datetime
import random 
import csv

#cl variable CEDA is 420 chunks of size 1, for 5 requests, do chunk size of 85 to avoid any cache overlap
ARRAY_SIZE = 600
NREQUESTS = 30
MAXCHUNKSIZE = int(ARRAY_SIZE/NREQUESTS)

def load_from_https(uri):
   """
   opening https file from uri using fsspec and pyfive
   """
   client_kwargs = {'auth': None}
   fs = fsspec.filesystem('http', **client_kwargs)
   http_file = fs.open(uri, 'rb')
   
   # We pass the raw http_file to pyfive; it will lazily read slices later
   ds = pyfive.File(http_file)
   print(f"Dataset reference established: {uri}")
   return ds


def _iterate_range_slice(ds_var, start_idx, end_idx):
    """
    Fetches a specific chunk size to isolate data volume performance.
    """

    start_time = time.perf_counter()
    start_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")
    try:
        # Request a precise block size (chunk_size)
        data = ds_var[start_idx : end_idx] 
        latency = time.perf_counter() - start_time
        end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
        return {"status": "success", "slice_latency": latency, "index": start_idx,"start-clock":start_clock,  "end-clock": end_clock}
    except Exception as exc:
        latency = time.perf_counter() - start_time
        end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
        error_cause = exc.__cause__ if hasattr(exc, '__cause__') else exc
        error_msg = f"HTTP {error_cause.status}" if isinstance(error_cause, ClientResponseError) else str(exc)
        return {"status": "failed", "error": error_msg, "slice_latency": latency, "index": start_idx,"start-clock":start_clock, "end-clock": end_clock}


"""
def random_ranges(chunk_size):
    gap = ARRAY_SIZE - (NREQUESTS * chunk_size)
    if gap < 0:
        raise ValueError(f"Chunk size {chunk_size} too large.{gap}")

    # Random gaps before, between and after the chunks
    gaps = [0] + sorted(random.sample(range(gap + NREQUESTS), NREQUESTS)) + [gap + NREQUESTS]

    start = 0
    ranges = []
    for i in range(NREQUESTS):
        start += gaps[i + 1] - gaps[i]
        ranges.append((start, start + chunk_size - 1))
        start += chunk_size
    print("CHECK RANGES: ",ranges)
    return ranges
"""


def random_ranges(chunk_size):
    if chunk_size * NREQUESTS > ARRAY_SIZE:
        raise ValueError(
            f"Chunk size {chunk_size} too large. "
            f"Maximum is {ARRAY_SIZE // NREQUESTS}"
        )

    gap = ARRAY_SIZE - (NREQUESTS * chunk_size)

    # There are NREQUESTS + 1 gaps:
    # before the first chunk, between chunks, and after the last chunk.
    # Generate NREQUESTS random split points to distribute `gap`.
    split_points = sorted(
        random.sample(range(gap + NREQUESTS), NREQUESTS)
    )

    gaps = []
    previous = -1

    for point in split_points:
        gaps.append(point - previous - 1)
        previous = point

    gaps.append(gap - sum(gaps))

    ranges = []
    start = gaps[0]

    for i in range(NREQUESTS):
        ranges.append((start, start + chunk_size - 1))
        start += chunk_size + gaps[i + 1]

    print("CHECK RANGES:", ranges)

    return ranges

# ------------------------------------------
# --- Configuration which server testing ---
# ------------------------------------------

current_test = 'JASMIN' 

servers = {
  'CEDA': {
    #'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/AerChemMIP/MOHC/UKESM1-0-LL/ssp370SST-lowNTCF/r1i1p1f2/Amon/cl/gn/latest/cl_Amon_UKESM1-0-LL_ssp370SST-lowNTCF_r1i1p1f2_gn_205001-209912.nc",
    #'var': "cl"
    #'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-1-LL/piControl/r1i1p1f2/Amon/ta/gn/latest/ta_Amon_UKESM1-1-LL_piControl_r1i1p1f2_gn_274301-274912.nc",
    #'var': "ta"
    #'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/AerChemMIP/MOHC/UKESM1-0-LL/ssp370SST-lowNTCF/r1i1p1f2/Amon/cl/gn/v20200420/cl_Amon_UKESM1-0-LL_ssp370SST-lowNTCF_r1i1p1f2_gn_201501-204912.nc", # cl 420 chunks size 1 of 1.13 MB
    #Below to compare to DKRZ
    #'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-0-LL/1pctCO2/r1i1p1f2/Amon/clw/gn/v20190406/clw_Amon_UKESM1-0-LL_1pctCO2_r1i1p1f2_gn_185001-189912.nc",
    #'var': "clw"

    #apples to apples
    'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc",
    'var': "cl"
  },
  'DKRZ': {
    #'uri': "http://esgf3.dkrz.de/thredds/fileServer/cmip6/RFMIP/MPI-M/MPI-ESM1-2-LR/piClim-spAer-anthro/r1i1p1f2/Amon/clw/gn/v20190710/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc",
    #'var': "clw"
    #apples to apples
    'uri': "http://esgf3.dkrz.de/thredds/fileServer/cmip6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc",
    'var': "cl"
  },
  'JASMIN': {
    #'uri': "https://gws-access.jasmin.ac.uk/public/canari/varsiha/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc",
    #'var': "clw"
    #apples to apples
    'uri': "https://gws-access.jasmin.ac.uk/public/canari/varsiha/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc",  # cl 420 chunks size 1 of 1.13 MB
    'var': "cl"
  }
}


HTTPS_URL = "http://esgf3.dkrz.de/thredds/fileServer/cmip6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc"
HTTPS_URL = "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc"
HTTPS_URL = "https://gws-access.jasmin.ac.uk/public/canari/varsiha/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc"



if current_test not in servers:
  raise ValueError(f"Unknown server: {current_test}. Choose from {list(servers.keys())}")

csv_filename = f"performance_results_{current_test}_{datetime.now().strftime("%d%b%Y%H%M%S")}.csv"

# Write headers to CSV
with open(csv_filename, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["maxWorkers", "chunkSize", "StartIndex", "Status", "Error",  "StartClock", "EndClock","Slice_Latency"])

config = servers[current_test]
print(f"--- Running Test on {current_test} ---")

# Setup the global-like dataset pointer
file_obj = load_from_https(config['uri'])
ds_var = file_obj[config['var']]

# Track total test execution time
total_start = time.perf_counter()

#cl variable is 420 chunks of size 1, for 20 requests, do chunk size of 21 to avoid any cache overlap
nWorkers = [1,2,5,10,15,20,25,30]#,2,3,4,5,15]#,6,7,8,9,10,11,12,13,14,15]#,20]#,25,30,40,50]
#setChunkSize = [1,2,3,4,5,6,7,8,9,10,20,25,30,35,40]

setChunkSize = [5,10,15]#2,3,4,5,6,7,8,9,10,20,25,30,35,40]

#calling function to get random ranges not overlapping so we dont have cache issues for each randomly chosen chunk size
results = {
    size: random_ranges(size)
    for size in setChunkSize #random.sample(range(1, MAXCHUNKSIZE),10)   # 10 unique chunk sizes
}

for max_worker in nWorkers:
    for chunk_size, ranges in results.items():
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_worker) as executor:
            # 1. Pass 'tracker' as an argument to each thread function
            futures = [ 
                executor.submit(_iterate_range_slice, ds_var, range[0], range[1]) 
                for range in ranges 
            ]

            #print(futures)
            #print(f"-- Results for maxWorkers={max_worker} and chunkSize={chunk_size} for {NREQUESTS} Requests --")
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    
                    if result["status"] == "success":
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] completed | maxWorkers: {max_worker}| Latency: {result['slice_latency']:.4f}s ")
                        
                        with open(csv_filename, mode='a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                max_worker, 
                                chunk_size, 
                                result['index'],
                                result["status"],
                                "None",
                                result['start-clock'],
                                result['end-clock'],
                                f"{result['slice_latency']:.4f}"
                            ])

                    else:
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] FAILED | Error: {result['error']} | maxWorkers: {max_worker}| Latency: {result['slice_latency']:.4f}s")
                        
                        with open(csv_filename, mode='a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                max_worker, 
                                chunk_size, 
                                result['index'],
                                result["status"],
                                result['error'],
                                result['start-clock'],
                                result['end-clock'],
                                f"{result['slice_latency']:.4f}"
                            ])
                            
                except Exception as crash:
                    #print(f"Thread for index range completely crashed before returning result: {crash}")
                    with open(csv_filename, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            max_worker, 
                            chunk_size, 
                            "Unknown",
                            "crashed",
                            str(crash),
                            "None",
                            "None",
                            "None",
                            0
                        ])

#print(f"--- Test Finished in {time.perf_counter() - total_start:.2f} seconds ---")