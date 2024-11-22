#include "passageSearch.h"

PS::Vertex *removeMiniF(std::list<PS::Vertex *> &alst);

/*
 * feature function
 *
 */
PS::PPEdge::PPEdge(VoriGraphVertex *psg1, VoriGraphVertex *psg2, double cost, std::list<topo_geometry::Halfedge> *path)
        : psg1(psg1), psg2(psg2), cost(cost), path(path) {};



/*
 *tools for this cpp only
 */
PS::Vertex *removeMiniF(std::list<PS::Vertex *> &alst) {
    std::list<PS::Vertex *>::iterator mini_it = alst.begin();
    for (std::list<PS::Vertex *>::iterator it = ++(alst.begin()); it != alst.end(); it++) {
        if ((*it)->f < (*mini_it)->f) {
            mini_it = it;
        }
    }
    PS::Vertex *mini_ptr = (*mini_it);
    alst.erase(mini_it);
    return mini_ptr;
}
