import gc
import pickle
from utils.edgeGdfPreprocessing import edgePreprocessing
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
import os

class LookUpTable:
    def __init__(self, locationRequest, filename, windowIdDictFilename, generateNewTable=False, parameterForTableIni = None):
        self.temperature = locationRequest.temperature
        self.mass = locationRequest.mass
        self.day = locationRequest.dayOfTheWeek
        self.time = locationRequest.timeOfTheDay
        self.request = self.__getRequest()
        self.windowIdDict = dict()
        self.windowIdDictFilename = windowIdDictFilename
        if generateNewTable:
            holeTable = self.generate(parameterForTableIni)
            self.saveTable(filename, holeTable)
            self.lookUpTable = holeTable[self.request]
            print("look up table generated")
        else:
            self.lookUpTable = self.readTable(filename)
            print("look up table loaded")


    def __len__(self):
        return len(self.lookUpTable)

    def generate(self,parameterForTableIni):
        # MultiNum = 2
        # print("MultiProcess:" + MultiNum.__str__())
        table = dict()
        nodes, edges = parameterForTableIni.osmGraph.graphToGdfs()
        flg = 0
        for temp in parameterForTableIni.temperatureList:
            for m in parameterForTableIni.massList:
                for d in parameterForTableIni.dayList:
                    for t in parameterForTableIni.timeList:
                        tableRequest = tuple([temp, m, d, t])
                        table[tableRequest] = dict()
                        self.edgesDict = edgePreprocessing(nodes, edges, temp, m, d, t).to_dict('index')
                        windowFeatureList = []

                        # for i, w in tqdm(enumerate(parameterForTableIni.windowList)):
                        #     if flg == 0:
                        #         self.windowIdDict[w.getTup()] = i
                        #     numericalFeatures, categoricalFeatures = w.extractFeatures(self.edgesDict)
                        #     table[tableRequest][i] = parameterForTableIni.estimationModel.predict(numericalFeatures,categoricalFeatures)

                        windowFeatureList = []
                        for i, w in enumerate(parameterForTableIni.windowList):
                            if flg == 0:
                                self.windowIdDict[w.getTup()] = i
                            numericalFeatures, categoricalFeatures = w.extractFeatures(self.edgesDict)
                            windowFeatureList.append([numericalFeatures, categoricalFeatures])
                        if torch.cuda.is_available():
                            device = torch.device("cuda")
                        else:
                            device = torch.device("cpu")
                        numericalFeatures = torch.Tensor([x[0] for x in windowFeatureList]).to(device)
                        categoricalFeatures = torch.LongTensor([x[1] for x in windowFeatureList]).transpose(1,2).contiguous().to(device)
                        # without dataloader
                        # energyOfWindows = parameterForTableIni.estimationModel.predictFromTensor(numericalFeatures, categoricalFeatures).tolist()
                        # for i in range(len(energyOfWindows)):
                        #     table[tableRequest][i] = energyOfWindows[i]
                        db = WindowFeatureDataLoader(numericalFeatures, categoricalFeatures)
                        del windowFeatureList,numericalFeatures, categoricalFeatures
                        gc.collect()
                        dloader = DataLoader(db, batch_size=524288, num_workers=0)
                        for step, (idx,n,c) in tqdm(enumerate(dloader)):
                            energyOfWindows = parameterForTableIni.estimationModel.predictFromTensor(n,c).tolist()
                        #print(energyOfWindows.shape)
                            for i in range(len(energyOfWindows)):
                                #print(i, idx[i].item())
                                table[tableRequest][idx[i].item()] = energyOfWindows[i]
                            del energyOfWindows
                            gc.collect()
                    flg = 1
        with open(self.windowIdDictFilename+".pkl", "wb") as tf:
            pickle.dump(self.windowIdDict, tf)
        return table

    def __calculateOneWindow(self, window, estimationModel):
        numericalFeatures, categoricalFeatures = window.extractFeatures(self.edgesDict)
        return estimationModel.predict(numericalFeatures, categoricalFeatures)

    def saveTable(self, filename, holeTable):
        folderOfLUTable = 'lookupTables'
        if not os.path.exists(folderOfLUTable):
            os.makedirs(folderOfLUTable)
        with open(os.path.join(folderOfLUTable,filename+".pkl"), "wb") as tf:
            pickle.dump(holeTable, tf)
        return

    def readTable(self, filename):
        folderOfLUTable = 'lookupTables'
        with open(os.path.join(folderOfLUTable,filename+".pkl"), "rb") as tf:
            loadDict = pickle.load(tf)
        with open(self.windowIdDictFilename+".pkl", "rb")as tf:
            self.windowIdDict = pickle.load(tf)
        return loadDict[self.request]

    def extractValue(self, window):
        return self.lookUpTable[self.windowIdDict[window.getTup()]]

    def __getRequest(self):
        return tuple([self.temperature, self.mass, self.day, self.time])


class WindowFeatureDataLoader:
    def __init__(self, numericalFeatures, categoricalFeatures):

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
        self.device = torch.device("cpu")
        self.numericalFeatures = numericalFeatures
        self.categoricalFeatures = categoricalFeatures
        #self.device = torch.device("cpu")
        #print(self.__getitem__(1))

    def __len__(self):
        return self.numericalFeatures.shape[0]

    def __getitem__(self, idx):
        return idx, self.numericalFeatures[idx,...], self.categoricalFeatures[idx,...]