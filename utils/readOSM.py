import xml.etree.ElementTree as ET
from utils.spaitalShape import Point, OdPair, Box
import os
from utils.osmgraph import GraphFromBbox, GraphFromHmlFile, GraphFromGdfs
import pandas as pd
import osmnx as ox
import geopandas as gpd

class XMLResource:
    def __init__(self, filename, zipLatLon=True):
        self.isZipped = zipLatLon
        self.ways, self.nodes = self.__readXML(filename)
        box = Box(-93.4975, -93.1850, 44.7458, 45.0045)
        self.paths = self.__getPaths(box)

    def __readXML(self, filename):
        domTree = ET.parse(filename)
        root = domTree.getroot()
        ways = root.findall("way")
        nodes = root.findall("node")
        return ways, nodes

    def __extractPathLength(self):
        pathLengthList = []
        for way in self.ways:
            nodeIDList = way.findall("nd")
            pathLengthList.append(len(nodeIDList))
        assert sum(pathLengthList) == len(self.nodes)
        return pathLengthList


    def __getPaths(self, box):
        startIndex = 0
        pathLengthList = self.__extractPathLength()
        trajList = []
        for pathLength in pathLengthList:
            pathNodeList = self.nodes[startIndex:startIndex + pathLength]
            startIndex += pathLength
            trajLat = []
            trajLon = []
            for pathNode in pathNodeList:
                lat = float(pathNode.get("lat"))
                lon = float(pathNode.get("lon"))
                point = Point(lon,lat)
                if not point.isContained(box):
                    break
                trajLat.append(lat)
                trajLon.append(lon)
            if len(trajLat):
                if self.isZipped:
                    trajList.append(list(zip(trajLat, trajLon)))
                else:
                    trajList.append([trajLat, trajLon])
        return trajList


class ReadOSMFile:

    def readGraph(self, newRestriction=True):
        boundingBox = Box(-93.4975, -93.1850, 44.7458, 45.0045)
        osmGraphInBbox = self.extractGraphOf(boundingBox)
        nodes, edges = osmGraphInBbox.nodesGdf, osmGraphInBbox.edgesGdf
        osmGraphInBbox.plotGraph()
        print(len(nodes),len(edges))
        print(edges.columns)
        if newRestriction:
            xml = XMLResource("../data/restrictionByMnDoT/Metro5.osm")
            print(xml.paths)
            self.outputTrajForMapMatching(xml.paths, "../results/restrictionPaths.csv")
            self.save_graph_shapefile_directional(osmGraphInBbox.graph, "../data/graph_shapefile")
        matchPathList  = self.mapMatchingPostprocessing()
        print(matchPathList)
        osmGraphInBbox.plotRoutes(matchPathList, edges, ['red', 'blue'], ['route1', 'route2'])

    def extractGraphOf(self, boundingBox):
        folderOfGraph = r'../Graphs/GraphDataInBbox' + str(boundingBox)
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

    def outputTrajForMapMatching(self, trajList, outputFile):
        list_wkt = []
        for i, traj in enumerate(trajList):
            wkt = "LINESTRING("
            for j in range(len(traj)-1):
                wkt += str(traj[j][1]) + " " + str(traj[j][0]) + ","
            wkt += str(traj[-1][1]) + " " + str(traj[-1][0]) + ")"
            list_wkt.append([i, wkt])
        df_wkt = pd.DataFrame(list_wkt, columns=['id', 'geom'])
        df_wkt.to_csv(outputFile, sep=";", index=False, line_terminator='\n')

    def save_graph_shapefile_directional(self, graph, filepath=None, encoding="utf-8"):
        # default filepath if none was provided
        if filepath is None:
            filepath = os.path.join(ox.settings.data_folder, "graph_shapefile")

        # if save folder does not already exist, create it (shapefiles
        # get saved as set of files)
        if not filepath == "" and not os.path.exists(filepath):
            os.makedirs(filepath)

        gdf_nodes, gdf_edges = ox.utils_graph.graph_to_gdfs(graph)
        filepath_nodes = os.path.join(filepath, "nodes.shp")
        filepath_edges = os.path.join(filepath, "edges.shp")

        # convert undirected graph to gdfs and stringify non-numeric columns
        gdf_nodes = ox.io._stringify_nonnumeric_cols(gdf_nodes)
        gdf_edges = ox.io._stringify_nonnumeric_cols(gdf_edges)
        # We need an unique ID for each edge
        gdf_edges["fid"] = gdf_edges.index
        # save the nodes and edges as separate ESRI shapefiles
        gdf_nodes.to_file(filepath_nodes, encoding=encoding)
        gdf_edges.to_file(filepath_edges, encoding=encoding)

    def mapMatchingPostprocessing(self):
        f_m = r'../data/mapMatchingResult/mr1.txt'
        df_matched = pd.read_csv(f_m, sep=";")
        df_matched.sort_values(by=['id'], inplace=True)
        df_matched["cpath_list"] = df_matched['cpath'].apply(lambda x: self.extract_path(x))
        return list(df_matched['cpath_list'])

    def extract_path(self, path):
        '''Divide the map-matched results connected by commas into a list.
        Args:
            opath: Map-matched results connected by commas
        Returns:
            A list of matched edges
        '''
        if (path == ''):
            return []
        elif isinstance(path, float):
            return int(path)
        return [int(s) for s in path.split(',')]


if __name__ == "__main__":
    rof = ReadOSMFile()
    rof.readGraph()
