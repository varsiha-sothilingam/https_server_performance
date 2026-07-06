import concurrent.futures
import numpy as np
import fsspec
import pyfive

# --- Dynamic Monkey-Patching for Latency and Task ID Logs ---
import asyncio
from datetime import datetime
from fsspec.implementations.http import HTTPFileSystem
import logging

logger = logging.getLogger("fsspec.http")

# Define the custom async function to override fsspec's default handler
async def logged_cat_file(self, url, start=None, end=None, **kwargs):
    """
    Read latency from asyncio D. Westwood (Monkey-patched version)
    """
    kw = self.kwargs.copy()
    kw.update(kwargs)
    logger.debug(url)

    if start is not None or end is not None:
        if start == end:
            return b""
        headers = kw.pop("headers", {}).copy()

        headers["Range"] = await self._process_limits(url, start, end)
        kw["headers"] = headers
    
    session = await self.set_session()
    
    # Track current Task ID running inside fsspec's internal event loop
    current_task = asyncio.current_task()
    task_id = id(current_task) if current_task else "NoTask"
    
    print(f'{datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")}: {task_id} - {url} - {kw}')
    
    async with session.get(self.encode_url(url), **kw) as r:
        out = await r.read()
        print(f'{datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")}: {task_id}:HTTPFileSystem._cat_file:249 recv')
        self._raise_not_found_for_status(r, url)
        
    return out

# Swap out fsspec's internal implementation with our custom timed block
HTTPFileSystem._cat_file = logged_cat_file
# ------------------------------------------------------------


def load_from_https(uri):
  """
  opening https file from uri using fsspec and pyfive
  """
  client_kwargs = {'auth': None}
  fs = fsspec.filesystem('http', **client_kwargs)
  http_file = fs.open(uri, 'rb')

  ds = pyfive.File(http_file)
  print(f"Dataset loaded from https with Pyfive: {uri}")
  return ds


def _iterate_range(i, multiplier=1):
    """
    to iterate over various slices of the dataset: D. Westwood
    """
    return ds[i*multiplier:(i+1)*multiplier]


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

config = servers[current_test]
print(f"--- Running Test on {current_test} ---")

file_obj = load_from_https(config['uri'])
ds = file_obj[config['var']]

# Define maximum concurrent workers
max_workers = 10

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
  futures = []

  # Changed 'workers' to 'max_workers' to avoid NameError
  for i in range(max_workers):
    print("Thread ", i, " submitted")
    future = executor.submit(_iterate_range, i, 1000)
    futures.append(future)

  print("-- Checking completed threads-- ")
  for future in concurrent.futures.as_completed(futures):
    try:
      s = future.result()
      print("Thread ", np.shape(s)[0]," completed with Success")
    except Exception as exc:
      print(f"Thread failed with exception: {exc}")