from fmm import Network,NetworkGraph,STMATCH,STMATCHConfig
from fmm import GPSConfig,ResultConfig
import time
import os
import gc
from os import walk

networkFilePath = r'D:/STUDYYYYYYYY/UMN/Research/Volvo/ecorouting/data/graph_shapefile/edges.shp'
network = Network(networkFilePath,"fid","u","v")
# output filepath
filepath = r'D:/STUDYYYYYYYY/UMN/Research/Volvo/ecorouting/data/mapMatchingResult'
if not os.path.exists(filepath):
    os.makedirs(filepath)
print "Nodes {} edges {}".format(network.get_node_count(),network.get_edge_count())
graph = NetworkGraph(network)
model = STMATCH(network,graph)
k = 10
gps_error = 0.3
radius = 20
#radius = 100
vmax = 30
factor = 1.5
stmatch_config = STMATCHConfig(k, radius, gps_error, vmax, factor)
cnt = 0
#for f, m, n in walk(r'./trajectory_005'):
trajPath = r'D:/STUDYYYYYYYY/UMN/Research/Volvo/ecorouting/data/restrictionTraj'
for f, m, n in walk(trajPath):
    print f,m,n
    if n:
        for fn in n:
            print fn
            cnt += 1
            start_time = time.time()
            # Define input data configuration
            input_config = GPSConfig()
            filename = f+"/"+fn
            input_config.file = filename
            input_config.id = "id"
            print input_config.to_string()
            # Define output configuration
            result_config = ResultConfig()
            result_config.file = os.path.join(filepath, 'mr'+str(cnt)+'.txt')
            #result_config.file = "network_005/mr_stmatch.txt"
            result_config.output_config.write_opath = True
            print result_config.to_string()
            status = model.match_gps_file(input_config, result_config, stmatch_config)
            print status
            print("--- %s seconds ---" % (time.time() - start_time))
