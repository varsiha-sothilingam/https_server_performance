import concurrent.futures
import time
import numpy as np
import fsspec
import pyfive
from aiohttp import ClientResponseError # Import to catch the specific HTTP error
from datetime import datetime
import random 
import csv



import logging

# 1. Set up a basic console logger
#logging.basicConfig(level=logging.WARNING)

# 2. Force fsspec and aiohttp to print detailed DEBUG logs
#logging.getLogger("fsspec").setLevel(logging.DEBUG)
#logging.getLogger("aiohttp.client").setLevel(logging.DEBUG)


#cl variable CEDA is 420 chunks of size 1, for 5 requests, do chunk size of 85 to avoid any cache overlap
ARRAY_SIZE = 420
NREQUESTS = 15
MAXCHUNKSIZE = int(ARRAY_SIZE/NREQUESTS)
print(MAXCHUNKSIZE)


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
    try:
        # Request a precise block size (chunk_size)
        data = ds_var[start_idx : end_idx] 
        latency = time.perf_counter() - start_time
        end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
        return {"status": "success", "latency": latency, "index": start_idx, "end-clock": end_clock}
    except Exception as exc:
        latency = time.perf_counter() - start_time
        end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
        error_cause = exc.__cause__ if hasattr(exc, '__cause__') else exc
        error_msg = f"HTTP {error_cause.status}" if isinstance(error_cause, ClientResponseError) else str(exc)
        return {"status": "failed", "error": error_msg, "latency": latency, "index": start_idx, "end-clock": end_clock}


def random_ranges(chunk_size):
    gap = ARRAY_SIZE - NREQUESTS * chunk_size
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

    return ranges


# ------------------------------------------
# --- Configuration which server testing ---
# ------------------------------------------

current_test = 'CEDA' 

servers = {
  'CEDA': {
    'uri': "https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/AerChemMIP/MOHC/UKESM1-0-LL/ssp370SST-lowNTCF/r1i1p1f2/Amon/cl/gn/latest/cl_Amon_UKESM1-0-LL_ssp370SST-lowNTCF_r1i1p1f2_gn_205001-209912.nc",
    'var': "cl"
  },
  'DKRZ': {
    'uri': "http://esgf3.dkrz.de/thredds/fileServer/cmip6/RFMIP/MPI-M/MPI-ESM1-2-LR/piClim-spAer-anthro/r1i1p1f2/Amon/clw/gn/v20190710/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc",
    'var': "clw"
  },
  'JASMIN': {
    'uri': "https://gws-access.jasmin.ac.uk/public/canari/varsiha/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc",
    'var': "clw"
  }
}

if current_test not in servers:
  raise ValueError(f"Unknown server: {current_test}. Choose from {list(servers.keys())}")

csv_filename = f"performance_results_{current_test}_{datetime.now().strftime("%d%b%Y%H%M%S")}.csv"

# Write headers to CSV
with open(csv_filename, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["maxWorkers", "chunkSize", "StartIndex", "Status", "Error",  "EndClock", "Latency"])


config = servers[current_test]
print(f"--- Running Test on {current_test} ---")

# Setup the global-like dataset pointer
file_obj = load_from_https(config['uri'])
ds_var = file_obj[config['var']]

# Track total test execution time
total_start = time.perf_counter()

#cl variable is 420 chunks of size 1, for 20 requests, do chunk size of 21 to avoid any cache overlap
nWorkers = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]#,20]#,25,30,40,50]
#setChunkSize = [1,2,3,4,5,6,7,8,9,10,20,25,30,35,40]

setChunkSize = [5]#,2,3,4,5,6,7,8,9,10,20,25,30,35,40]

#calling function to get random ranges not overlapping so we dont have cache issues for each randomly chosen chunk size
results = {
    size: random_ranges(size)
    for size in setChunkSize #random.sample(range(1, MAXCHUNKSIZE),10)   # 10 unique chunk sizes
}

for chunk_size, ranges in results.items():
    print(f"{chunk_size}: {ranges}")


for max_worker in nWorkers:
    for chunk_size, ranges in results.items():
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_worker) as executor:
            # Notice we pass ds_var explicitly to avoid relying on global scopes inside threads safely
            #futures = {executor.submit(_iterate_range, ds_var, i): i for i in range(NREQUESTS)}
            futures = [ executor.submit(_iterate_range_slice, ds_var, range[0], range[1]) 
                        for range in ranges ]

            print(futures)
            print(f"-- Results for maxWorkers={max_worker} and chunkSize={chunk_size} for {NREQUESTS} Requests --")
            for future in concurrent.futures.as_completed(futures):
                #idx = futures[future]
                try:
                    result = future.result()
                    if result["status"] == "success":
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] completed | Latency: {result['latency']:.4f}s | End-clock: {result['end-clock']}")
                        with open(csv_filename, mode='a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                max_worker, 
                                chunk_size, 
                                result['index'],
                                result["status"],
                                "None",
                                result['end-clock'],
                                result['latency']
                            ])

                    else:
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] completed  FAILED | Error: {result['error']} | Latency: {result['latency']:.4f}s | End-clock: {result['end-clock']}")
                        with open(csv_filename, mode='a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                max_worker, 
                                chunk_size, 
                                result['index'],
                                result["status"],
                                result['error'],
                                result['end-clock'],
                                result['latency']
                            ])
                except Exception as crash:
                    print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] completed   completely crashed before returning result: {crash}")
                    with open(csv_filename, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            max_worker, 
                            chunk_size, 
                            result['index'],
                            result["status"],
                            result['error'],
                            result['end-clock'],
                            result['latency']
                        ])

print(f"--- Test Finished in {time.perf_counter() - total_start:.2f} seconds ---")





