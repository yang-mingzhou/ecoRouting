from utils.osmgraph import GraphFunctions
from utils.spaitalShape import Point, OdPair, Box
import time
import osmnx as ox
import pickle
import itertools
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
        time = timeOfTheDay
        self.timeOfTheDay = self.calTimeStage(time)
        self.boundingBox = boundingBox

    def calTimeStage(self, t):
        return t // 4 + 1


class ParameterForTableIni:
    '''
    Used in trainNewLUTable
    Define the bins of lookup table
        daylist = [0, 1, 2,..., 7] 0 => unknown, 1 => Monday, ...
        timeList = [0, 1, 2, 3, 4, 5, 6] 0 => unknow, 1 => 12pm -4am, 2 => 4am-8am, ...
        mass: in the unit of kg
    '''
    def __init__(self):
        self.temperatureList = [1]
        # mean, min, max, est
        self.massList = [23000, 15875, 36287, 31751]
        self.dayList = [1]
        self.timeList = [3, 4]


def main():
    # A trip is composed a sequence of o-d pairs
    tripList = [
    [(44.98184729840299, -93.21901507372945), (44.786736270002265, -93.46675015774838), (44.17707635424199, -93.93739234659743), (44.06691076060971, -93.50769869525858), (44.98184729840299, -93.21901507372945)],
    [(44.98184729840299, -93.21901507372945), (44.786736270002265, -93.46675015774838), (44.17707635424199, -93.93739234659743), (44.98184729840299, -93.21901507372945)],
    [(44.98184729840299, -93.21901507372945), (44.454086469960494, -93.17591848620144), (44.98184729840299, -93.21901507372945)],
    [(44.98184729840299, -93.21901507372945), (44.989664361362806, -93.40828280308729), (44.98184729840299, -93.21901507372945)],
    [(44.98184729840299, -93.21901507372945), (45.05622822219631, -93.26844895683685), (45.090111537648816, -93.40307364125155), (44.98184729840299, -93.21901507372945)],
    [(44.98184729840299, -93.21901507372945), (44.98930327388153, -93.35529921740897), (44.786736270002265, -93.46675015774838), (44.98184729840299, -93.21901507372945)]
    ]

    routeList = [
        ["Route #1",
         ["Murphy Logistics Solutions",
          "Shakopee Distribution Center",
          "Johnson Outdoors",
          "Winegar Inc",
          "Murphy Logistics Solutions"]],

        ["Route #2",
         ["Murphy Logistics Solutions",
          "Shakopee Distribution Center",
          "Johnson Outdoors",
          "Murphy Logistics Solutions"]],

        ["Route #3",
         ["Murphy Logistics Solutions",
          "McLane - Northfield",
          "Murphy Logistics Solutions"]],

        ["Route #4",
         ["Murphy Logistics Solutions",
          "Core-Mark - Plymouth",
          "Murphy Logistics Solutions"]],

        ["Route #7",
         ["Murphy Logistics Solutions",
          "Murphy - Fridley Distribution Center",
          "LCS Communications",
          "Murphy Logistics Solutions"]],

        ["Route #10",
         ["Murphy Logistics Solutions",
          "Heinrich Envelope Corp",
          "Shakopee Distribution Center",
          "Murphy Logistics Solutions"]]
    ]


    flagFirstIter = True
    for i in range(len(routeList)):
        print("working on ", routeList[i][0])
        pathList = []
        totalEcotoll = 0
        totalTime = 0
        totalLength = 0
        for j in range(len(routeList[i][1])-1):
            # Murphy depot => Shakopee East (Depot)
            origin, destination = Point(tripList[i][j][1], tripList[i][j][0]), Point(tripList[i][j+1][1], tripList[i][j+1][0])
            temperature = 1
            mass = 23000
            # Monday
            dayOfTheWeek = 1
            # 9am
            timeOfTheDay = 9
            bigBbox = True
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
            if flagFirstIter:
                graphWithElevation = GraphFunctions.loadGraph(locationRequest)
                newLookUpTable = False
                flagFirstIter = False
            else:
                newLookUpTable = False

            # eco-routing
            # the result trajectory will be saved in "./results/filename"
            trajFileName = 'eco{}_from{}_to{}.json'.format(routeList[i][0], routeList[i][1][j], routeList[i][1][j+1]).replace(" ", "_")
            ecoEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'fuel', filename = trajFileName,
                                                                                     usingLookUpTable=True, newLookUpTable = newLookUpTable, lookUpTableName= lookupTableName, parameterForTableIni = ParameterForTableIni())

            # shortest route
            # shortestNodePath = GraphFunctions.findShortestPath(graphWithElevation, locationRequest)
            # shortestPath = GraphFunctions.nodePathTOEdgePath(shortestNodePath, edges)
            # GraphFunctions.calAndPrintPathAttributes(graphWithElevation, shortestPath, "shortestPath")

            # fastest route
            # the result trajectory will be saved in "./results/filename"
            # fastestEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'time', filename = str(i)+str(j)+'fastestRoute.json', usingLookUpTable=True, newLookUpTable = True, parameterForTableIni = ParameterForTableIni())
            # fastPaths[i,j] = fastestEdgePath
            # dictRes[(i, j, "fast")] = (length, energy, time)

            # save the routing results to the "./results/filename.html"
            #GraphFunctions.plotRoutes([ecoEdgePath, fastestEdgePath], graphWithElevation.getEdges(), ['green', 'red'], filename='routingresults', labels=['eco route', 'fastest route'])
            #plotRoutes([ecoEdgePath, fastestEdgePath, shortestPath], graphWithElevation.getEdges(), ['green','red','blue'], 'routingresults', ['eco route','fastest route','shortest route'])

            pathList.append(ecoEdgePath)
            totalEcotoll += energy
            totalTime += time
            totalLength += length
        GraphFunctions.plotRoutes(pathList, graphWithElevation.getEdges(), ['green'],
                                  filename='routingresults'+str(i+1), labels=['subRoute'+str(x) for x in range(len(routeList[i][1])-1)])
        print("totalEcotoll: {}, totalTime: {}, totalLength: {}".format(totalEcotoll, totalTime, totalLength))

if __name__ == '__main__':
    main()



