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
        # self.massList = [15875, 17009, 36287, 31751]
        self.massList = [17009]
        # self.massList = [23000]
        self.dayList = [1]
        self.timeList = [2]


def main():
    # A trip is composed a sequence of o-d pairs
    tripList = [
        [(29.484872, -98.383906), (29.402339, -98.361387), (29.484872, -98.383906)],  # Route 1
        # [(29.484872, -98.383906), (29.478114, -98.394193), (29.484872, -98.383906)],  # Route 2
        [(29.484872, -98.383906), (29.479033, -98.358569), (29.484872, -98.383906)],  # Route 3
        [(29.484872, -98.383906), (29.547943, -98.407558), (29.484872, -98.383906)],  # Route 4
        [(29.484872, -98.383906), (29.416654, -98.405843), (29.484872, -98.383906)],  # Route 5
        [(29.484872, -98.383906), (29.480669, -98.594265), (29.484872, -98.383906)],  # Route 6
        [(29.484872, -98.383906), (29.354772, -98.433148), (29.484872, -98.383906)],  # Route 7
        [(29.484872, -98.383906), (29.378519, -98.456973), (29.484872, -98.383906)],  # Route 8
        [(29.484872, -98.383906), (29.596528, -98.416812), (29.484872, -98.383906)]  # Route 9
    ]

    routeList = [
        ["Route #1", ["Charger", "Super Regional Distribution Center", "Charger"]],
        # ["Route #2", ["Charger", "San Antonio Distribution Center", "Charger"]],
        ["Route #3", ["Charger", "S.A. 19-Corp #294", "Charger"]],
        ["Route #4", ["Charger", "S.A. 44-Corp #568", "Charger"]],
        ["Route #5", ["Charger", "S.A. 22-Corp #106", "Charger"]],
        ["Route #6", ["Charger", "S.A. 30-Corp #262", "Charger"]],
        ["Route #7", ["Charger", "S.A. 21-Corp #444", "Charger"]],
        ["Route #8", ["Charger", "S.A. 13-Corp #26", "Charger"]],
        ["Route #9", ["Charger", "EFC 5-Corp #766", "Charger"]]
    ]

    flagFirstIter = True
    for i in range(len(routeList)):
        print("working on", routeList[i][0])
        pathList = []
        totalEcotoll = 0
        totalTime = 0
        totalLength = 0
        for j in range(len(routeList[i][1])-1):
            # Murphy depot => Shakopee East (Depot)
            origin, destination = Point(tripList[i][j][1], tripList[i][j][0]), Point(tripList[i][j+1][1], tripList[i][j+1][0])
            temperature = 1
            mass = 17009
            # Monday
            dayOfTheWeek = 1
            # 9am
            timeOfTheDay = 6
            bigBbox = False
            lookupTableName = "lUTableForFuel_tx"
            if bigBbox:
                boundingBox = Box(-99.1445415, -97.34430425, 26.236030749999998, 31.1530685)
                # print(boundingBox)
            else:
                # small bounding box
                boundingBox = Box(-98.7451, -98.1903, 29.1905, 29.6332)
                lookupTableName = "lUTableForFuel_smallBbox_tx"
            # Request
            locationRequest = LocationRequest(origin, destination, temperature, mass, dayOfTheWeek , timeOfTheDay, boundingBox)

            # Loading graph (downloading it if not exist) and pre-processing
            if flagFirstIter:
                graphWithElevation = GraphFunctions.loadGraph(locationRequest)
                newLookUpTable = True
                flagFirstIter = False
            else:
                newLookUpTable = False

            # eco-routing
            # the result trajectory will be saved in "./results/filename"
            # trajFileName = 'eco{}_from{}_to{}.json'.format(routeList[i][0], routeList[i][1][j], routeList[i][1][j+1]).replace(" ", "_")
            # ecoEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'fuel', filename = trajFileName,
            #                                                                          usingLookUpTable=True, newLookUpTable = newLookUpTable, lookUpTableName= lookupTableName,
            #                                                                          parameterForTableIni = ParameterForTableIni())

            # shortest route
            # shortestNodePath = GraphFunctions.findShortestPath(graphWithElevation, locationRequest)
            # shortestPath = GraphFunctions.nodePathTOEdgePath(shortestNodePath, edges)
            # GraphFunctions.calAndPrintPathAttributes(graphWithElevation, shortestPath, "shortestPath")

            # fastest route
            # the result trajectory will be saved in "./results/filename"
            trajFileName = 'fastest{}_from{}_to{}.json'.format(routeList[i][0], routeList[i][1][j],
                                                           routeList[i][1][j + 1]).replace(" ", "_")
            fastestEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest,
                                                                                         mode = 'time', filename = trajFileName,
                                                                                         usingLookUpTable=True, newLookUpTable = newLookUpTable,
                                                                                         lookUpTableName= "lUTableForTime_tx", parameterForTableIni = ParameterForTableIni())
            # fastPaths[i,j] = fastestEdgePath
            # dictRes[(i, j, "fast")] = (length, energy, time)

            # save the routing results to the "./results/filename.html"
            #GraphFunctions.plotRoutes([ecoEdgePath, fastestEdgePath], graphWithElevation.getEdges(), ['green', 'red'], filename='routingresults', labels=['eco route', 'fastest route'])
            #plotRoutes([ecoEdgePath, fastestEdgePath, shortestPath], graphWithElevation.getEdges(), ['green','red','blue'], 'routingresults', ['eco route','fastest route','shortest route'])

            # pathList.append(ecoEdgePath)
            pathList.append(fastestEdgePath)
            totalEcotoll += energy
            totalTime += time
            totalLength += length
        GraphFunctions.plotRoutes(pathList, graphWithElevation.getEdges(), ['green'],
                                  filename='routingresults'+routeList[i][0], labels=['subRoute'+str(x) for x in range(len(routeList[i][1])-1)])
        print("totalEcotoll: {} liters, totalTime: {} seconds, totalLength: {} meters".format(totalEcotoll/100, totalTime, totalLength))

if __name__ == '__main__':
    main()



