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
    '''
    def __init__(self):
        self.temperatureList = [1]
        self.massList = [23000]
        self.dayList = [1]
        self.timeList = [3]


def main():
    nodeList = [Point(-93.2219, 44.979), Point(-93.2494,44.83755), Point(-93.4071, 44.9903), Point(-93.44845, 44.79405)]
    dictRes = {}
    ecoPaths = {}
    fastPaths = {}
    for i in range(len(nodeList)):
        for j in range(len(nodeList)):
            if i != j:
                # Murphy depot => Shakopee East (Depot)
                origin, destination = nodeList[i], nodeList[j]
                temperature = 1
                mass = 23000
                # Monday
                dayOfTheWeek = 1
                # 9am
                timeOfTheDay = 9
                bigBbox = False
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
                # Request
                locationRequest = LocationRequest(origin, destination, temperature, mass, dayOfTheWeek , timeOfTheDay, boundingBox)

                # Loading graph (downloading it if not exist) and pre-processing
                graphWithElevation = GraphFunctions.loadGraph(locationRequest)

                # eco-routing
                # the result trajectory will be saved in "./results/filename"
                ecoEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'fuel', filename = str(i)+str(j)+'ecoRoute.json', usingLookUpTable=True, newLookUpTable = True, parameterForTableIni = ParameterForTableIni())
                ecoPaths[i,j] = ecoEdgePath
                dictRes[(i, j, "eco")] = (length, energy, time)

                # shortest route
                # shortestNodePath = GraphFunctions.findShortestPath(graphWithElevation, locationRequest)
                # shortestPath = GraphFunctions.nodePathTOEdgePath(shortestNodePath, edges)
                # GraphFunctions.calAndPrintPathAttributes(graphWithElevation, shortestPath, "shortestPath")

                # fastest route
                # the result trajectory will be saved in "./results/filename"
                fastestEdgePath, length, energy, time = GraphFunctions.routingAndSaveResults(graphWithElevation, locationRequest, mode = 'time', filename = str(i)+str(j)+'fastestRoute.json', usingLookUpTable=True, newLookUpTable = True, parameterForTableIni = ParameterForTableIni())
                fastPaths[i,j] = fastestEdgePath
                dictRes[(i, j, "fast")] = (length, energy, time)

                # save the routing results to the "./results/filename.html"
                #GraphFunctions.plotRoutes([ecoEdgePath, fastestEdgePath], graphWithElevation.getEdges(), ['green', 'red'], filename='routingresults', labels=['eco route', 'fastest route'])
                #plotRoutes([ecoEdgePath, fastestEdgePath, shortestPath], graphWithElevation.getEdges(), ['green','red','blue'], 'routingresults', ['eco route','fastest route','shortest route'])
    schedulepermut = [[0]+list(x)+[0] for x in list(itertools.permutations(list(range(1,len(nodeList))), ))]
    ecoSchedule = []
    minEcoToll = 99999
    travelTime = 0
    length = 0
    for schedule in schedulepermut:
        ecoToll = 0
        travelTime = 0
        length = 0
        for i in range(len(schedule)-1):
            ecoToll += dictRes[(schedule[i], schedule[i+1], "eco")][1]
            travelTime += dictRes[(schedule[i], schedule[i+1], "eco")][2]
            length += dictRes[(schedule[i], schedule[i+1], "eco")][0]
        if ecoToll < minEcoToll:
            ecoSchedule = schedule
            minEcoToll = ecoToll
    pathList = []
    ecoTollList, travelTimeList, lengthList = [], [], []
    for i in range(len(ecoSchedule)-1):
        pathList.append(ecoPaths[ecoSchedule[i], ecoSchedule[i+1]])
        ecoTollList.append(dictRes[(ecoSchedule[i], ecoSchedule[i + 1], "eco")][1])
        travelTimeList.append(dictRes[(ecoSchedule[i], ecoSchedule[i + 1], "eco")][2])
        lengthList.append(dictRes[(ecoSchedule[i], ecoSchedule[i + 1], "eco")][0])
    GraphFunctions.plotRoutes(pathList, graphWithElevation.getEdges(), ['green', 'red','blue', "black"], filename='routingresults', labels=['route1', 'route2', 'route3','route4'])
    with open("file.pkl", "wb") as tf:
        pickle.dump(dictRes, tf)
    GraphFunctions.plotPointList({"Murphy Depot": [(-93.2219, 44.979)], "M. Amundson":[(-93.2494,44.83755)], "Core Mark International": [(-93.4071, 44.9903)], "Conklin Co Inc": [(-93.44845, 44.79405)] }, ['red' for _ in range(4)], 'points.html')
    print(ecoTollList, travelTimeList, lengthList)

if __name__ == '__main__':
    main()



