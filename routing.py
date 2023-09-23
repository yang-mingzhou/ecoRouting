import time
from utils.osmgraph import GraphFunctions
from utils.spaitalShape import Point, OdPair, Box
import osmnx as ox
# Profiling: python -m cProfile -o profile.pstats routing.py
# Visualize profile: snakeviz profile.pstats

# packages: torch, osmnx = 0.16.1, tqdm, bintrees, plotly

class LocationRequest:
    def __init__(self, origin, destination, temperature, mass, dayOfTheWeek , timeOfTheDay, boundingBox):
        '''
        :param origin: (longitude, latitude)
        :param destination: (longitude, latitude)
        :param temperature: 1  # temperature === 1 since we don't use temperature as a feature right now
        :param mass: kg
        :param dayOfTheWeek: Monday => 1
        :param timeOfTheDay: 9am => 9
        :param boundingBox: bounding box for eco-routing
        '''

        # (longitude, latitude)
        self.origin = origin
        # test
        #self.origin = Point(-93.4254, 44.7888)
        #self.origin = Point(-93.470167, 44.799720)
        #origin = Point(-93.2466, 44.8959)
        self.destination = destination
        #self.destination = Point(-93.230358, 44.973583)

        self.odPair = OdPair(self.origin, self.destination)
        self.temperature = temperature
        self.mass = mass
        # Monday
        self.dayOfTheWeek = dayOfTheWeek
        # 9 am
        self.timeOfTheDay = self.calTimeStage(timeOfTheDay)
        self.boundingBox = boundingBox

    def calTimeStage(self, t):
        return t // 4 + 1


class ParameterForTableIni:
    '''
    Used in trainNewLUTable
    Define the bins of lookup table
        daylist = [0, 1, 2,..., 7] 0 => unknown, 1 => Monday, ...
        timeList = [0, 1, 2, 3, 4, 5, 6] 0 => unknow, 1 => 12pm -4am, 2 => 4am-8am, ...
    '''
    def __init__(self):
        self.temperatureList = [1]
        self.massList = [23000]
        self.dayList = [1]
        self.timeList = [3]


def main():
    startTime = time.time()
    # Murphy depot => Shakopee East (Depot)
    origin, destination = Point(-93.2219, 44.979), Point(-93.4620, 44.7903)
    # Murphy Warehouse => Customer
    #origin, destination = Point(-93.22040114903187, 44.98307130632795), Point(-93.17755951168938, 44.453148930484716)
    # Customer => Murphy Warehouse
    #destination, origin = Point(-93.22040114903187, 44.98307130632795), Point(-93.17755951168938, 44.453148930484716)
    temperature = 1
    mass = 23000
    # Monday
    dayOfTheWeek = 1
    # 9am
    timeOfTheDay = 9

    bigBbox = False
    lookupTableName = "lUTableForFuel"
    if bigBbox:
        #big bounding box: from murphy company (-93.22025, 44.9827), travel 70 miles
        distance = 70
        distance = distance*1609.34 # mile->km
        bbox = ox.utils_geo.bbox_from_point((44.9827, -93.22025), dist=distance, project_utm = False, return_crs = False)
        boundingBox = Box(bbox[-1], bbox[-2], bbox[-3], bbox[-4])
        print(boundingBox)
    else:
        # small bounding box
        boundingBox = Box(-93.4975, -93.1850, 44.7458, 45.0045)
        lookupTableName = "lUTableForFuel_smallBbox"
    # Request
    locationRequest = LocationRequest(origin, destination, temperature, mass, dayOfTheWeek , timeOfTheDay, boundingBox)

    # Loading graph (downloading it if not exist) and pre-processing
    graphWithElevation = GraphFunctions.loadGraph(locationRequest)
    print("time used for loading graph:", time.time() - startTime)
    # eco-routing
    # the result trajectory will be saved in "./results/filename"
    ecoEdgePath,length, energy, travelTime = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'fuel',
                                                                            filename = 'ecoRoute.json', usingLookUpTable=True,
                                                                            newLookUpTable = False, lookUpTableName= lookupTableName, parameterForTableIni = ParameterForTableIni())

    # shortest route
    # shortestNodePath = GraphFunctions.findShortestPath(graphWithElevation, locationRequest)
    # shortestPath = GraphFunctions.nodePathTOEdgePath(shortestNodePath, edges)
    # GraphFunctions.calAndPrintPathAttributes(graphWithElevation, shortestPath, "shortestPath")

    # fastest route
    # the result trajectory will be saved in "./results/filename"
    # fastestEdgePath = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'time', filename = 'fastestRoute.json', usingLookUpTable=True, newLookUpTable = True, parameterForTableIni = ParameterForTableIni())

    # save the routing results to the "./results/filename.html"
    GraphFunctions.plotRoutes([ecoEdgePath], graphWithElevation.getEdges(), ['green'], filename='routingresults', labels=['eco route'])
    #plotRoutes([ecoEdgePath, fastestEdgePath, shortestPath], graphWithElevation.getEdges(), ['green','red','blue'], 'routingresults', ['eco route','fastest route','shortest route'])

    endTime = time.time()
    print("time used:" , endTime-startTime)

if __name__ == '__main__':
    main()



