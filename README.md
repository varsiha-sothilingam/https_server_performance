# HTTPS (```NGINX```) Server Testing

This repository is a consolidation of all server performance testing and data visualisation scripts. The testing was to understand the performance of HTTPS nginx servers when undergoing a large ```GET-RANGE``` request size and also a large number of concurrent ```GET-RANGE``` requests, which will be a key feature required in the ESGF nodes for CMIP7 datasets. 

## Modifications to environment libraries
1. ```fsspec```
In order to extract the exact HTTPS requests, the ```fspec``` library was modified in the --- file as shown below. This allowed for the exact requests to be printed, where the exact HTTPS ID sent and recieved, with the time stamps could be extracted and used to evaluate the latency. 

File location: ```.../miniconda3/envs/activestorage/lib/python3.14/site-packages/fsspec/implementations/http.py```
File modifications made to ```_cat_file(self, url, start=None, end=None, **kwargs)``` below:

```diff
    async def _cat_file(self, url, start=None, end=None, **kwargs):
+       request_id = uuid.uuid4().hex[:8]
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
+        print(
+           f'{datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")} '
+           f'{request_id} '
+           f'Range={headers["Range"]}'
+       )
       
        async with session.get(self.encode_url(url), **kw) as r:
            out = await r.read()
+           print(
+            f'{datetime.now().strftime("%d/%b/%Y:%H:%M:%S.%f")} '
+            f'{request_id} '
+            f'Range={headers["Range"]}'
+            f' Recieved'
+           )
            self._raise_not_found_for_status(r, url)
        return out
```

2. ```pyfive```
In order to see the errors of ```GET-RANGE``` requests, the ```pyfive``` library was also modified in order to see the exact HTTPS error number in order to debug failed/incompleted get-range requests:
pyfive/btree.py
File location: ```.../miniconda3/envs/activestorage/lib/python3.14/site-packages/pyfive/btree.py```
File modifications made to ```_filter_chunk(cls, chunk_buffer, filter_mask, filter_pipeline, itemsize)``` function.

```diff
    def _filter_chunk(cls, chunk_buffer, filter_mask, filter_pipeline, itemsize):
        """Apply decompression filters to a chunk of data."""
        num_filters = len(filter_pipeline)
        for i, pipeline_entry in enumerate(filter_pipeline[::-1]):
            # A filter is skipped is the bit corresponding to its index in the
            # pipeline is set in filter_mask
            filter_index = num_filters - i - 1  # 0 to num_filters - 1
            if filter_mask & (1 << filter_index):
                continue

            filter_id = pipeline_entry["filter_id"]
-            if filter_id == GZIP_DEFLATE_FILTER:
-                chunk_buffer = zlib.decompress(chunk_buffer)
+            if filter_id == GZIP_DEFLATE_FILTER:
+                try:
+                    chunk_buffer = zlib.decompress(chunk_buffer)
+                except Exception as _:
+                    raise chunk_buffer
            elif filter_id == SHUFFLE_FILTER:
                buffer_size = len(chunk_buffer)
                unshuffled_buffer = bytearray(buffer_size)
                step = buffer_size // itemsize
                for j in range(itemsize):
                    start = j * step
                    end = (j + 1) * step
                    unshuffled_buffer[j::itemsize] = chunk_buffer[start:end]
                chunk_buffer = unshuffled_buffer
            elif filter_id == FLETCH32_FILTER:
                cls._verify_fletcher32(chunk_buffer)
                # strip off 4-byte checksum from end of buffer
                chunk_buffer = chunk_buffer[:-4]
            elif filter_id == LZF_FILTER:
                try:
                    import lzf
                except ImportError as e:
                    raise ModuleNotFoundError(
                        "LZF codec requires optional package 'python-neo-lzf'."
                        "Could be installed from conda-forge or PyPI."
                    ) from e
                uncompressed_len = struct.unpack(">H", chunk_buffer[:2])[0]
                chunk_buffer = lzf.decompress(chunk_buffer, uncompressed_len)
            else:
                raise NotImplementedError(
                    "Filter with id: %i import not supported" % (filter_id)
                )
        return chunk_buffer
```






## Testing Scripts
The main script to used to test the performance of the HTTPS servers is ```minimumScript.py```. This is an expansion of the minimum/ simple script originally created to test the performance of the HTTPS servers without dependencies on the PyActiveStorage (See: https://github.com/varsiha-sothilingam/PyActiveStorage-Testing/blob/master/scripts/test_httpsCEDA.py). This script can be modified to test over different numbers of maxWorkers, slice range sizes and the number of tests done per setting. When multiple tests are made, a different part of the axis which is being sliced is chosen to reduce biases due to caching of neighbouring and overlapping chunks.

The ```test_https_servers.py``` script is taken from PyActiveStorage tests which are developed for the GitHubActions. It is kept here for inspiration and comparison. 


## Running Scripts
The main script to run the tests is ```runLocalTests.sh```. This allows for local tests produce the correct .output files allowing one to view the individual HTTPS requests being sent.

The tests can be performed on a cluster such as LOTUS at the JASMIN facility however due to testing only small slice ranges, it is not more efficient. For future reference slurm scripts to submit the jobs are left here for future testing ideas such as ```submit_jobs.sh```,  ```submit_jobs_template.sh``` and  ```testconfigs.sh```.

## Reading the raw data output files

Raw data logs and csv files containing information of tests performed can be found in the following directories. Old tests are kept in order to understand if the performance has changed when configurations of the remote HTTPS server are modified. Each test has a ```.csv``` file and a ```.output``` file which can be matched with the date and time found in the name of both files. 

The ```.csv``` file provides metrics of the tests performed and their latency. It indicates:
* ```maxWorkers```: which is set in ```concurrent.futures.ThreadPoolExecutor(max_workers=max_worker)```
* Range slice & ```StartIndex```: (The rangeSlice is unfortunately sometimes named as ```chunkSize``` due to the fact that the chunk size is 1 but that should not always be assumed when testing for files of different chunk size). This provides the size of the slice requested in the test. The ```StartIndex``` provides information as to where on the axis the test has been performed. 
* ```Error```: This provides errors outputted by ```pyfive``` due to a failed or incompleted get-range request. Typically one may observe ```503``` errors due to files being offline or ```429``` if the request is too large.
* ```EndClock``` & ```Latency```:  This provides the timing for the ```futures``` job to be completed. These time metrics can be considered like a "user experienced latency". 
* The total number of tests for a given value of maxWorkers and RangeSlice combination can be seen in the file. Multiple tests are ran to reduce statistical fluctuations. Each test is performed at a different position of the slice axis (see ```StartIndex```) such that there is no overlaps in the slice index ranges. This reduces biases that may be introduced due to caching of neighbouring chunks which will directly impact the latency from showing the true performance of the server.

Example of ```.csv``` output:

|maxWorkers|chunkSize|StartIndex|Status |Error|StartClock                 |EndClock                   |Slice_Latency|
|----------|---------|----------|-------|-----|---------------------------|---------------------------|-------------|
|1         |5        |2         |success|None |28/Jul/2026:13:25:35.928932|28/Jul/2026:13:25:36.626419|0.6975       |
|1         |5        |32        |success|None |28/Jul/2026:13:25:36.626710|28/Jul/2026:13:25:37.292094|0.6654       |
|1         |5        |38        |success|None |28/Jul/2026:13:25:37.292444|28/Jul/2026:13:25:37.913730|0.6213       |
|1         |5        |64        |success|None |28/Jul/2026:13:25:37.914024|28/Jul/2026:13:25:38.710351|0.7963       |


The ```.output``` file provides information of the exact HTTPS get range requests being made to the remote server. It records all the print statements created after the ```fsspec``` has been modified. To obtain data of the HTTPS requests for a given test the file must be read out in a specific manner. A set of tests completed for a given maxWorkers and chunkSize/sliceRange will begin with the following line ```-- Results for maxWorkers=1 and chunkSize=5 for 40 Requests -- ```. Following this will be lines showing the timestamp, request ID and byte range. If it is a request recieved it will say Recieved at the end of the line. To match the sent and recieved get-range requests, one can match the request IDs. All the HTTPS requests made in a given test will be printed. The requests of a test are followed by a line such as ```Thread for range[12,16] completed | Latency: 0.8348s ```. In this example, a line like this will therefore appear 40 times in the log file for all 40 request tests made for that maxWorker and slice range setting. A snippet of the log file can be found below. With the time stamps of the get range requests and recived requests, one can evaluate the latency of an individual request. 


```
-- Results for maxWorkers=1 and chunkSize=5 for 40 Requests -- 
28/Jul/2026:14:01:49.863470 6af0c60a Range=bytes=15652078-15733139
28/Jul/2026:14:01:49.863634 90cb554f Range=bytes=11975124-12870473
28/Jul/2026:14:01:49.863929 c6aa60a1 Range=bytes=15826721-15930431
28/Jul/2026:14:01:49.864063 4bafd6b9 Range=bytes=19624248-19703507
.
.
.
28/Jul/2026:14:01:49.911221 4bafd6b9 Range=bytes=19624248-19703507 Recieved
28/Jul/2026:14:01:49.918531 6af0c60a Range=bytes=15652078-15733139 Recieved
28/Jul/2026:14:01:49.918694 ef3c0bbe Range=bytes=11648622-11768139 Recieved
28/Jul/2026:14:01:49.919052 4f36d45d Range=bytes=11869467-11975123 Recieved
Thread for range[6,10] completed | Latency: 1.1085s 
28/Jul/2026:14:01:51.898596 8753e007 Range=bytes=64256437-64350430
28/Jul/2026:14:01:51.898644 74405a8c Range=bytes=67958953-68033485
28/Jul/2026:14:01:51.898700 21b07c71 Range=bytes=68033486-68105496
.
.
.
28/Jul/2026:14:01:51.914240 74405a8c Range=bytes=67958953-68033485 Recieved
28/Jul/2026:14:01:51.919659 f3222e1a Range=bytes=60193158-60249182 Recieved
28/Jul/2026:14:01:51.933760 21b07c71 Range=bytes=68033486-68105496 Recieved
Thread for range[12,16] completed | Latency: 0.8348s 
.
.
.
```

## Output directories of performance tests completed:

Below is a brief description and list of the output directories completed.
1. ```csv-outputs/```: csv outputs of old tests completed in July and August 2026
2. ```log-request-outputs/```: corresponding log files to tests compelted in July and August 2026
3. ```output-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912/```: The exact same file is tested on three different servers, CEDA-NGINX, DKRZ-NGINX and JASMIN-AWS-APACHE. The csv and log outputs are in this directory along with the comparison plots comparing the CEDA to each of the servers. 
    * CEDA:   https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc
    * DKRZ:   http://esgf3.dkrz.de/thredds/fileServer/cmip6/CMIP/MOHC/UKESM1-0-LL/esm-hist/r1i1p1f2/Amon/cl/gn/v20190723/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc
    * JASMIN: https://gws-access.jasmin.ac.uk/public/canari/varsiha/cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc

4. ```output-clw/```: Two ```clw``` files are compared on DKRZ and CEDA and the log/csv files can be found in this directory. Additionally the plots in this directory are from an older plotting script which is no longer used. The updated plots with the latest plotting/data visualisation script can be found in ```output-clw-UpdatedPlotting/```
    * CEDA: https://esgf.ceda.ac.uk/thredds/fileServer/esg_cmip6/CMIP6/CMIP/MOHC/UKESM1-0-LL/1pctCO2/r1i1p1f2/Amon/clw/gn/v20190406/clw_Amon_UKESM1-0-LL_1pctCO2_r1i1p1f2_gn_185001-189912.nc
    * DKRZ: http://esgf3.dkrz.de/thredds/fileServer/cmip6/RFMIP/MPI-M/MPI-ESM1-2-LR/piClim-spAer-anthro/r1i1p1f2/Amon/clw/gn/v20190710/clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc

6. ```plotting/```: This is an obselete set of plots which I might need later so keeping for now. 



## Meta on data files tested so far:

1. The ```cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912.nc``` file can be located on three different servers. 

    |Variable Information  |                    |
    |---------------|---------------------------|
    |name           |cl                         |
    |shape          |(600, 85, 144, 192)        |
    |dtype          |float32                    |
    |chunk size     |(1, 43, 72, 96)            |
    |chunk grid     |[600, 2, 2, 2]             |
    |total chunks   |4800                       |
    |chunk size     |1,188,864 bytes (1.13 MB)  |

2. The ```clw``` files are similar but differ in the number of chunks and distribution of data in the b-tree:

    |Variable Information  |                    |
    |---------------|---------------------------|
    |file           |clw_Amon_UKESM1-0-LL_1pctCO2_r1i1p1f2_gn_185001-189912.nc  |
    |name           |clw                         |
    |shape          |(600, 85, 144, 192)        |
    |dtype          |float32                    |
    |chunk size     |(1, 43, 72, 96)            |
    |chunk grid     |[600, 2, 2, 2]             |
    |total chunks   |4800                       |
    |chunk size     |1,188,864 bytes (1.13 MB)  |


    |Variable Information  |                    |
    |---------------|---------------------------|
    |file           |clw_Amon_MPI-ESM1-2-LR_piClim-spAer-anthro_r1i1p1f2_gn_184901-187912.nc |
    |name           |clw                        |
    |shape          |(372, 47, 96, 192)         |
    |dtype          |float32                    |
    |chunk size     |(1, 47, 96, 192)           |
    |chunk grid     |[372, 1, 1, 1]             |
    |total chunks   |372                        |
    |chunk size     |3,465,216 bytes (3.30 MB)  |




## Plotting Script

The plotting script to compare and visualise the ```.output``` files is ```plotEachRequest.py```.  In the script one must specifiy the location of the output files to be compared and their respective sites. This script will produce four PDF files:
   * 1_latency_vs_max_workers_CEDA_vs_DKRZ.pdf
   * 2_latency_vs_time_overlay.pdf
   * 3_latency_vs_clock_per_chunk_and_workers.pdf
   * 4_byte_range_histograms.pdf

Examples of the output can be seen in the ```output-clw-UpdatedPlotting/``` directory. 