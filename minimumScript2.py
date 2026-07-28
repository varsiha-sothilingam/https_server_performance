import concurrent.futures
import time
import numpy as np
import fsspec
import pyfive
from aiohttp import ClientResponseError # Import to catch the specific HTTP error
from datetime import datetime
import random 
import csv
import uuid


import logging

# 1. Set up a basic console logger
#logging.basicConfig(level=logging.WARNING)

# 2. Force fsspec and aiohttp to print detailed DEBUG logs
#logging.getLogger("fsspec").setLevel(logging.DEBUG)
#logging.getLogger("aiohttp.client").setLevel(logging.DEBUG)

import asyncio
import aiohttp

#cl variable CEDA is 420 chunks of size 1, for 5 requests, do chunk size of 85 to avoid any cache overlap
ARRAY_SIZE = 420
NREQUESTS = 20
MAXCHUNKSIZE = int(ARRAY_SIZE/NREQUESTS)
print(MAXCHUNKSIZE)
class RequestTracker:
    def __init__(self):
        self.http_records = []
        self._pending_requests = {}  # Maps params ID -> internal tracking dict
        self._lock = asyncio.Lock()

    async def on_request_start(self, session, trace_config_ctx, params):
        clock_now = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")
        t_start = time.perf_counter()
        
        # 1. Extract bytes range requested
        bytes_range = params.headers.get("Range", "Full-File")
        
        # 2. Check if client sent an explicit request ID header, or generate a unique tracking ID
        client_req_id = params.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        
        async with self._lock:
            # Store pending request state mapped to the unique params instance key
            self._pending_requests[id(params)] = {
                "internal_id": client_req_id,
                "start_clock": clock_now,
                "t_start": t_start,
                "bytes_range": bytes_range
            }

    async def on_request_end(self, session, trace_config_ctx, params):
        t_end = time.perf_counter()
        
        async with self._lock:
            # Match the ending request to its start data using id(params)
            pending_data = self._pending_requests.pop(id(params), None)
            
            if pending_data:
                # 3. Extract the server's response headers
                response_headers = params.response.headers if params.response else {}
                
                # Check standard server-side ID headers (X-Request-ID, X-Correlation-ID, etc.)
                server_req_id = (
                    response_headers.get("X-Request-ID") or 
                    response_headers.get("X-Correlation-ID") or 
                    response_headers.get("X-Server-Request-Id") or 
                    pending_data["internal_id"]  # Fallback to client-generated ID
                )
                
                # Verify match condition
                is_matched = (pending_data["internal_id"] == server_req_id) or (server_req_id != "Unknown")
                
                latency = t_end - pending_data["t_start"]
                
                # Record correlated request payload
                self.http_records.append({
                    "request_id": server_req_id,
                    "matched": is_matched,
                    "start_clock": pending_data["start_clock"],
                    "slice_latency": latency,
                    "bytes_range": pending_data["bytes_range"],
                    "http_status": params.response.status if params.response else 0
                })


#def load_from_https(uri):
#    async def get_session(**kwargs):
#        return aiohttp.ClientSession(trace_configs=[trace_config], **kwargs)
#    client_kwargs = {
#        'get_client': get_session,
#        'auth': None
#    }
#
#    
#    fs = fsspec.filesystem('http', **client_kwargs)
#    http_file = fs.open(uri, 'rb')
#    
#    ds = pyfive.File(http_file)
#    print(f"Dataset reference established: {uri}")
#    
#    return ds

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

#def _iterate_range_slice(ds_var, start_idx, end_idx, tracker):
#    start_time = time.perf_counter()
#    start_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")
#    
#    # Snapshot position in request records before slicing
#    initial_rec_idx = len(tracker.http_records)
#    
#    try:
#        data = ds_var[start_idx : end_idx] 
#        total_slice_latency = time.perf_counter() - start_time
#        end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
#        
#        # Extract HTTP records recorded specifically during this slice
#        slice_requests = tracker.http_records[initial_rec_idx:]
#        
#        return {
#            "status": "success", 
#            "slice_latency": total_slice_latency, 
#            "index": start_idx, 
#            "start-clock": start_clock,
#            "end-clock": end_clock,
#            "http_request_count": len(slice_requests),
#            "http_requests": slice_requests  # List of dicts: [{'start_clock': '...', 'latency': 0.12}, ...]
#        }
        
 # except Exception as exc:
 #     total_slice_latency = time.perf_counter() - start_time
 #     end_clock = datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")   
 #     
 #     error_cause = exc.__cause__ if hasattr(exc, '__cause__') else exc
 #     error_msg = f"HTTP {error_cause.status}" if isinstance(error_cause, ClientResponseError) else str(exc)
 #     
 #     return {
 #         "status": "failed", 
 #         "error": error_msg, 
 #         "slice_latency": total_slice_latency, 
 #         "index": start_idx, 
 #         "start-clock": start_clock,
 #         "end-clock": end_clock,
 #     }

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
    writer.writerow(["maxWorkers", "chunkSize", "StartIndex", "Status", "Error",  "StartClock", "EndClock","Slice_Latency"])



config = servers[current_test]
print(f"--- Running Test on {current_test} ---")

# Setup the global-like dataset pointer
file_obj = load_from_https(config['uri'])
ds_var = file_obj[config['var']]

# Track total test execution time
total_start = time.perf_counter()

#cl variable is 420 chunks of size 1, for 20 requests, do chunk size of 21 to avoid any cache overlap
nWorkers = [15]#,2,3,4,5,15]#,6,7,8,9,10,11,12,13,14,15]#,20]#,25,30,40,50]
#setChunkSize = [1,2,3,4,5,6,7,8,9,10,20,25,30,35,40]

setChunkSize = [10]#,2,3,4,5,6,7,8,9,10,20,25,30,35,40]

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
            # 1. Pass 'tracker' as an argument to each thread function
            futures = [ 
                executor.submit(_iterate_range_slice, ds_var, range[0], range[1]) 
                for range in ranges 
            ]

            print(futures)
            print(f"-- Results for maxWorkers={max_worker} and chunkSize={chunk_size} for {NREQUESTS} Requests --")
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    
                    if result["status"] == "success":
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] completed | Latency: {result['slice_latency']:.4f}s ")
                        
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
                        print(f"Thread for range[{result['index']},{result['index']+chunk_size-1}] FAILED | Error: {result['error']} | Latency: {result['slice_latency']:.4f}s")
                        
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
                    print(f"Thread for index range completely crashed before returning result: {crash}")
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

print(f"--- Test Finished in {time.perf_counter() - total_start:.2f} seconds ---")