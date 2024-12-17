#include "VoriConfig.h"


#include <iostream>
#include <assert.h>

using namespace std;


#define DOUBLE_VAR_METHOD(name)                                         \
double VoriConfig::name(){                                              \
  map<string, double>::iterator found = doubleConfigVars.find(#name);   \
  if(found == doubleConfigVars.end()){                                  \
    cerr<<"Did not find config var "<<#name<<"!"<<endl;                 \
    assert(0);                                                          \
  }                                                                     \
  return found->second;                                                 \
}                                                                                               

DOUBLE_VAR_METHOD(voronoiMinimumDistanceToObstacle);

DOUBLE_VAR_METHOD(topoGraphDistanceToJoinVertices);
DOUBLE_VAR_METHOD(topoGraphAngleCalcStartDistance);
DOUBLE_VAR_METHOD(topoGraphAngleCalcEndDistance);
DOUBLE_VAR_METHOD(topoGraphAngleCalcStepSize);
DOUBLE_VAR_METHOD(topoGraphMarkAsFeatureEdgeLength);

DOUBLE_VAR_METHOD(alphaShapeRemovalSquaredSize);

DOUBLE_VAR_METHOD(simiVerNumberOfExitsOffset);
DOUBLE_VAR_METHOD(simiVerNumberOfExitsMax);
DOUBLE_VAR_METHOD(simiVerExitAngleRadOffset);
DOUBLE_VAR_METHOD(simiVerExitAngleRadMax);

DOUBLE_VAR_METHOD(simiVerDistanceToObstaclesOffset);
DOUBLE_VAR_METHOD(simiVerDistanceToObstaclesMax);

DOUBLE_VAR_METHOD(simiVerDistanceBetweenJoinedVerticesOffset);
DOUBLE_VAR_METHOD(simiVerDistanceBetweenJoinedVerticesMax);

DOUBLE_VAR_METHOD(simiExitVertexDistanceOffset);
DOUBLE_VAR_METHOD(simiExitVertexDistanceMax);

DOUBLE_VAR_METHOD(simiExitDistanceToObstaclesOffset);
DOUBLE_VAR_METHOD(simiExitDistanceToObstaclesMax);

DOUBLE_VAR_METHOD(simiConsistencyEdgeDistanceFactor);
DOUBLE_VAR_METHOD(simiConsistencyEdgeDistanceMinAllowance);

DOUBLE_VAR_METHOD(simiIsomorphismMinNumberOfVertices);

DOUBLE_VAR_METHOD(simiNeighbourDistanceOffset);
DOUBLE_VAR_METHOD(simiNeighbourDistanceFactor);
DOUBLE_VAR_METHOD(simiNeighbourMaxHopDifference);
DOUBLE_VAR_METHOD(simiNeighbourMaxMajorHopDifference);

DOUBLE_VAR_METHOD(simiNeighbourMinProb);
DOUBLE_VAR_METHOD(simiNeighbourGoodProb);

DOUBLE_VAR_METHOD(firstDeadEndRemovalDistance);
DOUBLE_VAR_METHOD(secondDeadEndRemovalDistance);
DOUBLE_VAR_METHOD(thirdDeadEndRemovalDistance);
DOUBLE_VAR_METHOD(fourthDeadEndRemovalDistance);

