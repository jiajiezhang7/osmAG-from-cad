/*passageSearch:
 *
 * Author:  Yijun Yuan
 * date:    Jan.21.2018
 *
 * Here the passageSearch will attempt to build passage to passage graph
 * on top of previous roomGraph.
 */

#ifndef PASSAGESEARCH_H__
#define PASSAGESEARCH_h__

#include "VoriGraph.h"
#include "TopoGeometry.h"

namespace PS{
//1. struct PPEdge(passage1, passage2, cost, path)
struct Vertex{
    Vertex(VoriGraphVertex* VoriVptr, double h, double g):VoriVptr(VoriVptr),h(h){this->g=1000000;this->f=0;};
    VoriGraphVertex* VoriVptr;
    double h;
    double g;
    double f;
};
//2. general unit to form a flexible graph
class PPEdge{
    public:
    VoriGraphVertex* psg1;//from psg1 to psg2
    VoriGraphVertex* psg2;
    double cost;
    std::list<topo_geometry::Halfedge>* path;
    public:
    PPEdge(VoriGraphVertex* psg1, VoriGraphVertex* psg2, double cost, std::list<topo_geometry::Halfedge>* path);
};

 

}
#endif
