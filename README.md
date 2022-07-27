# ecoRouting
This is project of eco-efficient path selection given an origin/destination pair and a bounding box.


## Environments:

The code works well with [python](https://www.python.org/) 3.8.8, 
[pytorch](https://pytorch.org/) 1.8.1, 
and **[osmnx](https://github.com/gboeing/osmnx)  0.16.1**.

Some scripts (for map matching) require cygwin and python 2.7

## Pipeline:
1. Data preprocessing:
   
   (a) [Download the osm graph data](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/downloadGraph.py): Download the osm graph within the bounding box to the folder '/data/bbox'. We are using a bounding box: (min Longitude, max Longitude , min Latitude , max Latitude: -95.35305 -91.544 43.1759 45.891999999999996)  which contains 722629 edges and 277704 nodes.
      
   (b) [Trajectory generation](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/trajectoryGeneration.py): Extract and sample (by every 3 seconds) the trajectories of vehicles inside the bounding box for map matching (3646 trajectories in total).      

   (c) [Map matching](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/mapmatching.py) the trajectories with osm.

   (d) [Plot the map matching result](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/plotMapMatching.py) and save the figures of map matching results.

   (e) [Feature extraction](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/featureExtraction.py)

   (f) [Data preparing](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/dataPreparing.py)

2. Model definition

   (a) [Pretrain a node2vec model](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/node2vec.py)

   (b) [Dataloader](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/dataIterator.py)

   (c) [Define PiNN_D](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/pinn_d.py)
   
   (d) [Params of PiNN_D](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/config.py)


3. [Training](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/train.py)


4. [Testing](https://github.com/yang-mingzhou/ecoRouting/blob/main/code/dataPreparing.py)

[comment]: <> (## File Folders:)

[comment]: <> (1. )
   
   
[comment]: <> (## Files)

[comment]: <> (1. )

Change Log
-----

### 7/26/2022
Version 1.0 
