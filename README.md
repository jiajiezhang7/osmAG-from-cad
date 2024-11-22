# Area graph

## Paper 
The paper describing the method was accepted for publication at ICAR2019. The preprint version is [available on Arxiv](https://arxiv.org/abs/1910.01019).

Hou, J., Y. Yuan, and S. Schwertfeger,  "Area Graph: Generation of Topological Maps using the Voronoi Diagram",  19th International Conference on Advanced Robotics (ICAR): IEEE Press, 2019.

```
@conference {hou2019area,
	title = {Area Graph: Generation of Topological Maps using the Voronoi Diagram},
	booktitle = {19th International Conference on Advanced Robotics (ICAR)},
	year = {2019},
	publisher = {IEEE Press},
	organization = {IEEE Press},
	author = {Hou, Jiawei and Yuan, Yijun and Schwertfeger, S{\"o}ren}
}
```




## How to compile
### Dependencies
Before running the code, make sure you have installed: cmake, g++, Eigen3, Qt4, CGAL
They can be installed by (Ubuntu): 
```
sudo apt-get install g++
sudo apt-get install cmake
sudo apt-get install qt4-default
sudo apt-get install libcgal-dev
```
The code has been test on Ubuntu 14.04 and 16.04. 

### How to use
Now, we can build our Area Graph generation code:
```
cd /path/to/map-matching/code/
mkdir build
cd build
cmake ..
make example_segmentation
./bin/test_areaMatch Map.png resolution door_width corridor_width noise_percentage
```
where the meanings of the arguments are shown belows.
* Map.png: The map you are going to generate the Area Graph for it. Please don't use the maps whose background color is lighter than the sites (obstacle points).
* resolution: resolution of the map (the default resolution is set as 0.05)
* door_width: the widest door's width in the environment
* corridor_width: the narrowest corridor's width in the environment
if you don't know the door width and corridor width of the environment, set it as -1 and we use the fix W = 1.25 to run the Alpha Shape algorithm to detect rooms
* noise_percentage: You can rely on intuition to estimate how much noise is in the map. If you use the map in the directory "afterAlphaRemoval" as input, you can set this argument as 0.

example: 
```
./bin/example_segmentation ../dataset/input/Freiburg79_scan_furnitures_trashbins.png 0.05 -1 -1 1.5
```
or
```
./bin/example_segmentation ../dataset/input/Freiburg79_scan_furnitures_trashbins.png 0.05 0.85 2.7 1.5
```




