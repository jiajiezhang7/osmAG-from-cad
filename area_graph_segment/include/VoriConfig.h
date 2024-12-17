#ifndef VORI_CONFIG_H
#define VORI_CONFIG_H


#include <map>
#include <string>

struct VoriConfig{


  double voronoiMinimumDistanceToObstacle();

  double topoGraphDistanceToJoinVertices();

  double topoGraphAngleCalcStartDistance();
  double topoGraphAngleCalcEndDistance();
  double topoGraphAngleCalcStepSize();

  double topoGraphMarkAsFeatureEdgeLength();

  double alphaShapeRemovalSquaredSize();
  
  // for Vertices
  double simiVerNumberOfExitsOffset();
  double simiVerNumberOfExitsMax();

  double simiVerExitAngleRadOffset();
  double simiVerExitAngleRadMax();

  double simiVerDistanceToObstaclesOffset();
  double simiVerDistanceToObstaclesMax();

  double simiVerDistanceBetweenJoinedVerticesOffset();
  double simiVerDistanceBetweenJoinedVerticesMax();

  double simiExitVertexDistanceOffset();
  double simiExitVertexDistanceMax();

  double simiExitDistanceToObstaclesOffset();
  double simiExitDistanceToObstaclesMax();

  double simiConsistencyEdgeDistanceFactor();
  double simiConsistencyEdgeDistanceMinAllowance();

  double simiIsomorphismMinNumberOfVertices();

  double simiNeighbourDistanceOffset();
  double simiNeighbourDistanceFactor();

  double simiNeighbourMaxHopDifference();
  double simiNeighbourMaxMajorHopDifference();

  double simiNeighbourMinProb();
  double simiNeighbourGoodProb();

  double firstDeadEndRemovalDistance();
  double secondDeadEndRemovalDistance();

  double thirdDeadEndRemovalDistance();
  double fourthDeadEndRemovalDistance();


  std::map<std::string, double> doubleConfigVars;
  
};




#endif
