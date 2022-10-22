import networkx as nx
import osmnx as ox
import os
from utils.estimationModel import EstimationModel, MultiTaskEstimationModel
from utils.window import Window, WindowFromList
from collections import defaultdict
from  utils  import routingAlgorithms
from utils.lookUpTable import LookUpTable
from utils.edgeGdfPreprocessing import edgePreprocessing
import plotly.graph_objects as go
import numpy as np
import plotly
import pandas as pd
import gc
import json
import copy

class OsmGraph:

    def __init__(self, g):
        self.graph = g
        self.nodesGdf, self.edgesGdf = self.graphToGdfs()

    def saveHmlTo(self, folderAddress):
        ox.save_graphml(self.graph, filepath=os.path.join(folderAddress, 'osmGraph.graphml'))

    def graphToGdfs(self):
        nodes, edges = ox.graph_to_gdfs(self.graph, nodes=True, edges=True)
        if "u" not in edges.columns:
            edges = edges.reset_index()
        return nodes, edges

    def getEdges(self):
        _, edges = self.graphToGdfs()
        return edges

    def getEdgesDict(self):
        _, edges = self.graphToGdfs()
        return edges.to_dict('index')

    def getUToV(self):
        _, edges = self.graphToGdfs()
        self.uToV = defaultdict(list)
        edges.apply(lambda x: self.__update(x), axis=1)
        return self.uToV

    def __update(self,x):
        self.uToV[x.u].append((x.name, x.v))

    def getNodes(self):
        nodes, _ = self.graphToGdfs()
        return nodes

    def saveNodesLatLong(self, filename):
        nodes = self.getNodes()
        nodeLatLong = nodes[['y', 'x']]
        nodeLatLong.columns = ['latitude', 'longitude']
        nodeLatLong.to_csv(filename)
        return

    def removeIsolateNodes(self):
        self.graph.remove_nodes_from(list(nx.isolates(self.graph)))
        #self.nodesGdf, self.edgesGdf = self.graphToGdfs()

    def getNearestNode(self, yx):
        return ox.get_nearest_node(self.graph, yx, method='euclidean')

    def getODNodesFromODPair(self, odPair):
        origNode = self.getNearestNode(odPair.origin.yx())
        targetNode = self.getNearestNode(odPair.destination.yx())
        return origNode, targetNode

    def plotGraph(self,filename=None):
        fig, ax = ox.plot_graph(self.graph)
        if filename is not None:
            fig.savefig(filename)

    def plotPath(self, path, filename):
        fig, ax = ox.plot_graph_route(self.graph, path,node_size=5)
        fig.savefig(filename)

    def plotPathList(self, pathList, filename):
        fig, ax = ox.plot_graph_routes(self.graph, pathList, route_colors=['g', 'r', 'b'], node_size=5)
        fig.savefig(filename)

    def shortestPath(self, localRequest):
        origNode, destNode = self.getODNodesFromODPair(localRequest.odPair)
        shortestPath = nx.shortest_path(G=self.graph, source=origNode, target=destNode, weight='length')
        return shortestPath

    def ecoPath(self, localRequest, lookUpTable):
        self.origNode, self.destNode = self.getODNodesFromODPair(localRequest.odPair)
        self.estimationModel = EstimationModel("fuel")
        #ecoPath, ecoEnergy, ecoEdgePath = self.dijkstra()
        ecoPath, ecoEnergy, ecoEdgePath = self.aStar(localRequest, lookUpTable)
        return ecoPath, ecoEnergy, ecoEdgePath

    def fastestPath(self, localRequest, lookUpTable = None):
        self.origNode, self.destNode = self.getODNodesFromODPair(localRequest.odPair)
        self.estimationModel =EstimationModel("time")
        fastestPath, shortestTime, fastestEdgePath = self.dijkstra(localRequest, lookUpTable)
        return fastestPath, shortestTime, fastestEdgePath

    def dijkstra(self, localRequest, lookUpTable):
        if lookUpTable is None:
            routingModel = routingAlgorithms.Dijkstra(self.getEdgesDict(), self.getUToV(), self.origNode, self.destNode, self.estimationModel)
        else:
            routingModel = routingAlgorithms.DijkstraFromLUTable(self.getEdgesDict(), self.getUToV(), self.origNode, self.destNode,
                                 self.estimationModel, lookUpTable)
        return routingModel.routing()

    def aStar(self, localRequest, lookUpTable):
        if lookUpTable is None:
            routingModel = routingAlgorithms.AStar(self.getEdgesDict(), self.getUToV(), self.origNode, self.destNode, self.estimationModel,
                             localRequest, self.getNodes())
        else:
            routingModel = routingAlgorithms.AStarFromLUTable(self.getEdgesDict(), self.getUToV(), self.origNode, self.destNode,
                                 self.estimationModel, localRequest, self.getNodes(), lookUpTable)
        #print('initialized')
        return routingModel.routing()

    def extractAllWindows(self, lenthOfWindows):
        uToV = self.getUToV()
        windowList, tempWindowStack, tempNodeIdStack = [], [], []
        for i in uToV:
            listOfNodes = uToV[i]
            for edgeIdAndV in listOfNodes:
                edgeIdInGdf = edgeIdAndV[0]
                nextNodeId = edgeIdAndV[1]
                tempWindowStack.append([edgeIdInGdf])
                tempNodeIdStack.append(nextNodeId)
            tempWindowStack.append([-1])
            tempNodeIdStack.append(i)
            tempWindowStack.append([-1, -1])
            tempNodeIdStack.append(i)
        while tempWindowStack:
            tempWindow = list(tempWindowStack.pop())

            tempNode = tempNodeIdStack.pop()
            listOfNodes = uToV[tempNode]
            #print(tempWindow, tempNode,  listOfNodes)
            if len(tempWindow) == lenthOfWindows-1:
                tempWindow.append(-1)
                windowList.append(WindowFromList(tempWindow))
                tempWindow.pop()
                for edgeIdAndV in listOfNodes:
                    edgeIdInGdf = edgeIdAndV[0]
                    tempWindow.append(edgeIdInGdf)
                    #copy.deepcopy(tempWindow)
                    windowList.append(WindowFromList(tempWindow))
                    tempWindow.pop()
            else:
                for edgeIdAndV in listOfNodes:
                    edgeIdInGdf = edgeIdAndV[0]
                    nextNodeId = edgeIdAndV[1]
                    tempWindow.append(edgeIdInGdf)
                    #copy.deepcopy(tempWindow)
                    tempWindowStack.append(tuple(tempWindow))
                    tempNodeIdStack.append(nextNodeId)
                    tempWindow.pop()
        return windowList

    def totalLength(self, path):
        length = 0
        for i in path:
            length += self.edgesGdf.loc[i, 'length']
        return length

    def totalEnergy(self, path):
        #print(1)
        return self.__calculateValue(path, "fuel")

    def totalTime(self, path):
        return self.__calculateValue(path, "time")

    def __calculateValue(self, path, estimationType):
        edgeDict = self.getEdgesDict()
        pointList = []
        estimationModel = EstimationModel(estimationType)
        #estimationModel = EstimationModel(estimationType)
        value = 0
        firstSeg = path[0]
        window = Window(-1, -1, -1, firstSeg)
        # prevWindowSeg = -1
        for i in range(len(path)):
            window.minusSeg = window.prevSeg
            window.prevSeg = window.midSeg
            window.midSeg = window.sucSeg
            if i < len(path)-1:
                window.sucSeg = path[i+1]
            else:
                window.sucSeg = -1
            numericalFeatures, categoricalFeatures = window.extractFeatures(edgeDict)
            # print(numericalFeatures, categoricalFeatures)
            addValue = estimationModel.predictFromData(numericalFeatures, categoricalFeatures)
            value += addValue
            # if path[i] in [58029, 59122, 62170, 6004, 52169]:
            #     print(value)
            pointList.append((str(window.midSeg), numericalFeatures[1], categoricalFeatures[1], addValue, value))
        # self.__saveInformation(pointList,  path, estimationType)
        return value

    def __saveInformation(self, pointList, path, estimationType):
        f = estimationType+'.txt'
        filename = open(f, 'w')
        for p in pointList:
            filename.write(str(p) + "\n")
        filename.write("path: ")
        for p in path:
            filename.write(str(p) + ", ")
        filename.close()

    def __findSegId(self, path, i):
        OdPair = (path[i], path[i+1])
        segId = self.edgesGdf[self.edgesGdf['odPair'] == OdPair].index[0]
        return segId

    def __updateWindow(self, window, path, i):
        window.minusSeg = window.prevSeg
        window.prevSeg = window.midSeg
        window.midSeg = window.sucSeg
        if i < len(path) - 2:
            nextSeg = self.__findSegId(path, i+1)
            window.sucSeg = nextSeg
        else:
            window.sucSeg = -1
        return window


class GraphFromHmlFile(OsmGraph):
    def __init__(self, hmlAddress):
        self.graph = ox.load_graphml(hmlAddress)
        self.nodesGdf, self.edgesGdf = self.graphToGdfs()


class GraphFromBbox(OsmGraph):
    def __init__(self, boundingBox):
        self.graph = ox.graph_from_polygon(boundingBox.polygon(), network_type='drive')
        self.nodesGdf, self.edgesGdf = self.graphToGdfs()


class GraphFromGdfs(OsmGraph):
    def __init__(self, nodes, edges):
        self.graph = ox.utils_graph.graph_from_gdfs(nodes, edges)
        self.nodesGdf, self.edgesGdf = nodes, edges


class GraphFunctions():
    @staticmethod
    def __initGoFigure(lat, long, type='markers', label='default', size=5, color='red'):
        '''
        type = 'markers' or 'lines'
        lat/long: list, if 'type == lines'; float, else
        '''
        fig = go.Figure(go.Scattermapbox(
            name=label,
            mode=type,
            lon=long,
            lat=lat,
            marker={'size': size, 'color': color}))
        return fig

    @staticmethod
    def __addTrace(fig, lat, long, type='markers', label='default', size=5, color='red'):
        print(color)
        fig.add_trace(go.Scattermapbox(
            name=label,
            mode=type,
            lon=long,
            lat=lat,
            marker={'size': size, 'color': color}))
        return fig

    @staticmethod
    def plot_traj(data):
        lat = data['gps_Latitude'].tolist()
        long = data['gps_Longitude'].tolist()
        # adding the lines joining the nodes
        fig = go.Figure(go.Scattermapbox(
            name="Path",
            mode="lines",
            lon=long,
            lat=lat,
            marker={'size': 10},
            line=dict(width=4.5, color='blue')))
        # getting center for plots:
        lat_center = np.mean(lat)
        long_center = np.mean(long)
        # defining the layout using mapbox_style
        fig.update_layout(mapbox_style="stamen-terrain",
                          mapbox_center_lat=30, mapbox_center_lon=-80)
        # for different trips, maybe you should modify the zoom value
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox={
                              'center': {'lat': lat_center,
                                         'lon': long_center},
                              'zoom': 14})
        # you can change the name of the figure saved
        # pio.write_image(fig,'trajectory.png')
        # fig.write_html("results/file.html")
        fig.show()

    @staticmethod
    def calAndPrintPathAttributes(osmGraph, edgePath, pathname):
        numberOfSegments = len(edgePath)
        length = osmGraph.totalLength(edgePath)
        energy = osmGraph.totalEnergy(edgePath)
        time = osmGraph.totalTime(edgePath)
        print(pathname + ":" + f"{numberOfSegments} segments, {length} meters, {energy} liters, {time} seconds")
        return length, energy, time

    # plot map matching results
    @staticmethod
    def plotRoutes(routeList, network_gdf, colorList, filename, labels=None):
        '''
        colorList: len(colorList) == len(routeList) => Assign each route a color;
                    len(colorList) == 1 => represent all route with the same color
        '''
        if labels is None:
            labels = ['path' for _ in range(len(routeList))]
        if len(colorList) == 1:
            color = colorList[0]
            colorList = [color for _ in range(len(routeList))]
        directory = './results'
        if not os.path.exists(directory):
            os.makedirs(directory)
        edgeLongList = []
        edgeLatList = []
        for i in range(len(routeList)):
            route = routeList[i]
            long_edge = []
            lat_edge = []
            for j in route:
                e = network_gdf.loc[j]
                if 'geometry' in e:
                    xs, ys = e['geometry'].xy
                    z = list(zip(xs, ys))
                    l1 = list(list(zip(*z))[0])
                    l2 = list(list(zip(*z))[1])
                    for k in range(len(l1)):
                        long_edge.append(l1[k])
                        lat_edge.append(l2[k])
            if i == 0:
                fig = go.Figure(go.Scattermapbox(
                    name=labels[i],
                    mode="lines",
                    lon=long_edge,
                    lat=lat_edge,
                    marker={'size': 5, 'color': colorList[i]},
                    line=dict(width=3, color=colorList[i])))
            else:
                fig.add_trace(go.Scattermapbox(
                    name=labels[i],
                    mode="lines",
                    lon=long_edge,
                    lat=lat_edge,
                    marker={'size': 5, 'color': colorList[i]},
                    line=dict(width=3, color=colorList[i])))
        # getting center for plots:
        lat_center = np.mean(lat_edge)
        long_center = np.mean(long_edge)
        zoom = 9.5
        # defining the layout using mapbox_style
        fig.update_layout(mapbox_style="stamen-terrain",
                          mapbox_center_lat=30, mapbox_center_lon=-80)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox={
                              'center': {'lat': lat_center,
                                         'lon': long_center},
                              'zoom': zoom})

        plotly.offline.plot(fig, filename=os.path.join(directory, filename + '.html'), auto_open=True)

    @staticmethod
    def __plotFigAndSave(fig, lat_center, long_center, filename):
        fig.update_layout(mapbox_style="stamen-terrain",
                          mapbox_center_lat=30, mapbox_center_lon=-80)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox={
                              'center': {'lat': lat_center,
                                         'lon': long_center},
                              'zoom': 9.5})
        plotly.offline.plot(fig, filename=filename, auto_open=False)
        return

    @staticmethod
    def plotPointList(pointDict, colorList, filename):
        '''
        pointDict: {"label": list of points}
        '''
        i = 0
        for label in pointDict:
            lat, long = zip(*pointDict[label])
            # adding the lines joining the nodes
            if i == 0:
                fig = GraphFunctions.__initGoFigure(lat, long, type='markers', label=label, size=15, color=colorList[i])

            else:
                fig = GraphFunctions.__addTrace(fig, lat, long, type='markers', label=label, size=15, color=colorList[i])
            i += 1
        # getting center for plots:
        lat_center = np.mean(lat)
        long_center = np.mean(long)
        GraphFunctions.__plotFigAndSave(fig, lat_center, long_center, filename)

    @staticmethod
    def saveRoutes(route, network_gdf, filename):
        directory = './results'
        if not os.path.exists(directory):
            os.makedirs(directory)

        long_edge = []
        lat_edge = []
        for j in route:
            e = network_gdf.loc[j]
            if 'geometry' in e:
                xs, ys = e['geometry'].xy
                z = list(zip(xs, ys))
                l1 = list(list(zip(*z))[0])
                l2 = list(list(zip(*z))[1])
                for k in range(len(l1)):
                    long_edge.append(l1[k])
                    lat_edge.append(l2[k])
        with open(os.path.join(directory, filename), 'w') as f:
            # indent=2 is not needed but makes the file human-readable
            json.dump(list(zip(lat_edge, long_edge)), f, indent=2)

        # with open("ecoRouteLong.json", 'w') as f:
        #     # indent=2 is not needed but makes the file human-readable
        #     json.dump(long_edge, f, indent=2)
        # with open("ecoRouteLat.json", 'w') as f:
        #     # indent=2 is not needed but makes the file human-readable
        #     json.dump(lat_edge, f, indent=2)

    @staticmethod
    def trainNewLUTable(paramForTable, graphWithElevation, locationRequest, filename, windowIdDictFilename, mode='fuel'):
        windowList = graphWithElevation.extractAllWindows(4)
        print(len(windowList))
        GraphFunctions.__addTableParams(paramForTable, windowList, graphWithElevation, mode)
        del windowList
        gc.collect()
        lookUpTable = LookUpTable(locationRequest, filename, windowIdDictFilename, generateNewTable=True,
                                  parameterForTableIni=paramForTable)
        return lookUpTable

    @staticmethod
    def __addTableParams(paramForTable, windowList, osmGraph, estMode):
        paramForTable.windowList = windowList
        paramForTable.osmGraph = osmGraph
        paramForTable.estMode = estMode
        paramForTable.estimationModel = EstimationModel(estMode)

    @staticmethod
    def extractGraphOf(boundingBox):
        folderOfGraph = r'Graphs/GraphDataInBbox' + str(boundingBox)
        print(folderOfGraph)
        if os.path.exists(os.path.join(folderOfGraph, 'osmGraph.graphml')):
            print("reloading graph..")
            osmGraph = GraphFromHmlFile(os.path.join(folderOfGraph, 'osmGraph.graphml'))
        else:
            if not os.path.exists(folderOfGraph):
                os.makedirs(folderOfGraph)
            print("downloading graph..")
            osmGraph = GraphFromBbox(boundingBox)
            osmGraph.saveHmlTo(folderOfGraph)
        # fig, ax = ox.plot_graph(osmGraph.graph)
        return osmGraph

    @staticmethod
    def extractElevation(nodes, edges, boundingBox):
        GraphFunctions.extractNodesElevation(nodes, boundingBox)
        GraphFunctions.extractEdgesElevation(nodes, edges)

    @staticmethod
    def extractNodesElevation(nodes, boundingBox):
        filename = "nodesWithElevation" + str(boundingBox) + ".csv"
        nodesElevation = pd.read_csv(os.path.join("statistical data", filename), index_col=0)
        nodes['indexId'] = nodes.index
        nodes['elevation'] = nodes.apply(lambda x: nodesElevation.loc[x['indexId'], 'MeanElevation'], axis=1)

    @staticmethod
    def extractEdgesElevation(nodesWithElevation, edges):
        edges['uElevation'] = edges['u'].apply(lambda x: nodesWithElevation.loc[x, 'elevation'])
        edges['vElevation'] = edges['v'].apply(lambda x: nodesWithElevation.loc[x, 'elevation'])

    @staticmethod
    def extractGraphInMurphy(nodes, edges):
        edgesInMurphy = GraphFunctions.extractEdgesInMurphy(edges)
        graphInMurphy = GraphFromGdfs(nodes, edgesInMurphy)
        return graphInMurphy

    @staticmethod
    def extractEdgesInMurphy(edges):
        edges['uvPair'] = edges.apply(lambda x: (x.u, x.v), axis=1)
        segmentElevationChange = np.load('statistical data/segmentElevationChange.npy', allow_pickle=True).item()
        edges['isInMurphy'] = edges.uvPair.apply(lambda x: x in segmentElevationChange)
        return edges[edges.isInMurphy]

    @staticmethod
    def findShortestPath(osmGraph, localRequest):
        shortestPath = osmGraph.shortestPath(localRequest)
        print("shortestPath:", shortestPath)
        # ox.plot_graph(osmGraph)
        # osmGraph.plotPath(shortestPath, "shortest route.pdf")
        return shortestPath

    @staticmethod
    def findEcoPathAndCalEnergy(osmGraph, localRequest, lookUpTable):
        ecoPath, ecoEnergy, ecoEdgePath = osmGraph.ecoPath(localRequest, lookUpTable)
        print("ecoPath:", ecoPath, "ecoEnergy:", ecoEnergy, ecoEdgePath)
        # osmGraph.plotPath(ecoPath, "eco route.pdf")
        return ecoPath, ecoEnergy, ecoEdgePath

    @staticmethod
    def findFastestPathAndCalTime(osmGraph, localRequest, lookUpTable):

        fastestPath, shortestTime, fastEdgePath = osmGraph.fastestPath(localRequest, lookUpTable)
        print("fastestPath:", fastestPath, "shortestTime:", shortestTime, fastEdgePath)
        # osmGraph.plotPath(fastestPath,"fastest route.pdf")
        return fastestPath, shortestTime, fastEdgePath

    @staticmethod
    def nodePathTOEdgePath(nodePath, edgesGdf):
        edgePath = []
        for i, OdPair in enumerate(zip(nodePath[:-1], nodePath[1:])):
            segmentId = edgesGdf[edgesGdf['odPair'] == OdPair].index[0]
            edgePath.append(segmentId)
        return edgePath

    @staticmethod
    def loadGraph(locationRequest):
        '''

        '''
        osmGraphInBbox = GraphFunctions.extractGraphOf(locationRequest.boundingBox)
        nodes, edges = osmGraphInBbox.graphToGdfs()

        # extract elevation change of edges
        GraphFunctions.extractElevation(nodes, edges, locationRequest.boundingBox)

        # preprocess the edges
        edges = edgePreprocessing(nodes, edges, locationRequest.temperature, locationRequest.mass,
                                  locationRequest.dayOfTheWeek, locationRequest.timeOfTheDay)

        graphWithElevation = GraphFromGdfs(nodes, edges)
        graphWithElevation.removeIsolateNodes()
        print('Graph loaded!')
        return graphWithElevation

    @staticmethod
    def routingAndSaveResults(graphWithElevation, locationRequest, mode, filename, usingLookUpTable, newLookUpTable = False, parameterForTableIni = None):
        '''
        Input:
            graphWithElevation => (OSMGraph) Input Graph
            locationRequest => (LocationRequest) Input request
            mode => (stirng) 'fuel': ecorouting; 'time': fastest routing
            filename => 'string': filename of the output trajectory
            usingLookUpTable => (boolean) True: use LookUpTable method
            newLookUpTable => (boolean) True: generate a new lookup table
            parameterForTableIni => (ParameterForTableIni) params used to generate the lookup table
        Return:
            routing results: represented by the edge id in OSM
        Output file:
            the GPS trajectory of the routing result
        '''
        if usingLookUpTable:
            # filename for lookup table
            lutablefilename = "lUTableForTime" if mode == 'time' else "lUTableForFuel"
            # filename for lookup table
            windowIdDictFilename = "./results/windowIdDict"
            if newLookUpTable:
                lookUpTable = GraphFunctions.trainNewLUTable(parameterForTableIni, graphWithElevation, locationRequest,
                                                             lutablefilename, windowIdDictFilename, mode=mode)
            else:
                # load table from filename.pkl
                lookUpTable = LookUpTable(locationRequest, lutablefilename, windowIdDictFilename)
        else:
            lookUpTable = None

        if mode == "time":
            path, _, edgePath = GraphFunctions.findFastestPathAndCalTime(graphWithElevation,locationRequest, lookUpTable)
            length, energy, time = GraphFunctions.calAndPrintPathAttributes(graphWithElevation, edgePath, "fastestPath")

        else:
            # eco route
            path, _, edgePath = GraphFunctions.findEcoPathAndCalEnergy(graphWithElevation, locationRequest, lookUpTable)
            length, energy, time = GraphFunctions.calAndPrintPathAttributes(graphWithElevation, edgePath, "ecoRoute")

        GraphFunctions.saveRoutes(edgePath, graphWithElevation.getEdges(), filename)
        return edgePath, length, energy, time