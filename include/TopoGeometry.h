#ifndef TOPO_GEOMETRY_H
#define TOPO_GEOMETRY_H

#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>

#include <boost/geometry/geometries/adapted/boost_tuple.hpp>

#define EPSINON 0.00000001
BOOST_GEOMETRY_REGISTER_BOOST_TUPLE_CS(cs::cartesian)

namespace topo_geometry{

typedef boost::geometry::model::d2::point_xy<double> point;

static double getX(const point &p){
  return boost::geometry::get<0>(p);
}
static double getY(const point &p){
  return boost::geometry::get<1>(p);
}

// boost::geometry::distance


    /* Jiawei: crate a polygon DS */

    struct polygon{
        std::list<point> points;
    };

static std::string print(const point &p){
  std::stringstream str;
  str<<getX(p)<<", "<<getY(p);
  return str.str();
}

// comparison for 2D coordinates - in order to put them in a map
struct Smaller{
    bool operator() (const point &one, const point &two) const {
      if( boost::geometry::get<0>(one) == boost::geometry::get<0>(two)) return boost::geometry::get<1>(one) < boost::geometry::get<1>(two);
      return boost::geometry::get<0>(one) < boost::geometry::get<0>(two);
    }
};

class Vertex{
public:

  point p;

};
    //add from yutianyan
// comparison for 2D coordinates - in order to judge whether the path is cut from source or target
// set as static to avoid multiple definition
    static bool operator==(const point &one, const point &two) {
        return (boost::geometry::get<0>( one ) == boost::geometry::get<0>( two )) &&
               (boost::geometry::get<1>( one ) == boost::geometry::get<1>( two ));
    }
/** Jiawei **/
//    static bool operator==(const point &one, const point &two) {
//        return (fabs(boost::geometry::get<0>( one ) - boost::geometry::get<0>( two ))<EPSINON) &&
//               (fabs(boost::geometry::get<1>( one ) - boost::geometry::get<1>( two ))<EPSINON);
//    }

class Halfedge{ //这是原始的vori图里的边（由两个点直接相连而成的短线段），最后生成的topo图里的一个halfedge（class TopoHalfEdge）里则包含许多这种halfedges（class Halfedge）
  public:
    Halfedge(point s, point t, point o, double dist, bool isRay=false):s_(s), t_(t), o_(o), dist_(dist), isRay_(isRay){ calcLength(); }
    Halfedge(){};
    point s() const { return s_;} //< start point
    point t() const { return t_;} //< target point
    point o() const { return o_;} //< obstacle point：最近障碍物位置

    double dist() const { return dist_;} //< distance to obstacle point：到最近障碍物的距离
    double length() const { return length_;} //< length
    
    bool isRay() const { return isRay_;}

    //add from yutianyan
    //cut halfedge at a certain length
    //return a list of halfedge, when list size equals:
    //0: fail to cut;
    //1: cutting normally
    //2: cutting at source/target
    std::list<Halfedge> cutHalfedge(point cutfrom, double cutlength) {
        //list to save the cut halfedge
        std::list<Halfedge> edgeCutted;
        if ((cutlength - EPSINON > length_) || (cutlength + EPSINON < 0)) {
            //0. can not cut at the point out of the halfedge
            return edgeCutted;
        } else {
            //1. normal cutting (2 Halfedges in result)
            if ((cutlength - EPSINON > 0) && (cutlength + EPSINON < length_)) {
                double rate = 0;
                if (cutfrom == s_) {
                    rate = cutlength / length_;
                } else {
                    if (cutfrom == t_) {
                        rate = 1 - cutlength / length_;
                    } else {
                        //point must be start or target vertex of the halfedge
                        return edgeCutted;
                    }
                }

                point cutposition( rate * getX( t_ ) + (1 - rate) * getX( s_ ),
                                   rate * getY( t_ ) + (1 - rate) * getY( s_ ));
                Halfedge edgeCut_first( s_, cutposition, o_, dist_, isRay_ );
                Halfedge edgeCut_second( cutposition, t_, o_, dist_, isRay_ );

                edgeCutted.push_back( edgeCut_first );
                edgeCutted.push_back( edgeCut_second );
            } else {
                //2. cutting at source/target
                Halfedge edgeCut( s_, t_, o_, dist_, isRay_ );
                edgeCutted.push_back( edgeCut );
            }
            return edgeCutted;
        }
    }

  protected:
    
   double calcLength(){
      length_ = boost::geometry::distance(s_, t_);
      return length_;
    }

    /* Jiawei: create polygon face in here */

    polygon pol;

    point s_, t_, o_;
    double dist_, length_;
    bool isRay_;
};

}


#endif
