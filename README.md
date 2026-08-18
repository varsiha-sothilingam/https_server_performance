# HTTPS (NGINX) Server Testing

This repository is a consolidation of all server performance testing and data visualisation scripts. The testing was to understand the performance of HTTPS nginx servers when undergoing a large get-range request and also a large number of concurrent get-range requests, which will be a key feature required in the ESGF nodes for CMIP7 datasets. 
In order to extract the exact HTTPS requests, the ```fspec``` was modified in the --- file as shown below. This allowed for the exact requests to be printed, where the exact HTTPS id sent and recieved, with the time stamps could be extracted and used to evaluate the latency. 



In order to see the errors of get range requests, the pyfive was also modified like so: 