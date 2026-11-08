package net.osmand.router.junction;

import net.osmand.router.junction.JunctionGeometry.*;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntFunction;

/** Copies local source values only; accessors are not retained or used by the worker. */
public final class JunctionWindow {
    private JunctionWindow() { }
    public static Route copy(int pointCount,int decisionCount,int maneuver,
                             IntFunction<Geo> pointAt,IntFunction<Decision> decisionAt) {
        if (pointCount<2 || maneuver<0 || maneuver>=decisionCount) throw new IllegalArgumentException("Route window source");
        Decision selected=decisionAt.apply(maneuver);
        int anchor=selected.routeIndex, roundaboutEnd=selected.roundaboutEndIndex;
        if (anchor<0 || anchor>=pointCount) throw new IllegalArgumentException("Route window anchor");
        if (roundaboutEnd>=pointCount) throw new IllegalArgumentException("Roundabout end outside route");
        int first=anchor,last=anchor;double approach=0,departure=0;
        double atExit=-1;
        while (first>0 && approach<125 && anchor-first<4999) {
            approach+=JunctionCompiler.distance(pointAt.apply(first-1),pointAt.apply(first));first--;
        }
        while (last+1<pointCount && (departure<125 || last<roundaboutEnd || (atExit>=0 && departure-atExit<20)) && last-anchor<4999) {
            departure+=JunctionCompiler.distance(pointAt.apply(last),pointAt.apply(last+1));last++;
            if (last==roundaboutEnd) atExit=departure;
        }
        if ((first>0 && approach<125) || (last+1<pointCount && (departure<125 || last<roundaboutEnd || (atExit>=0 && departure-atExit<20)))) throw new IllegalArgumentException("Route window capacity");
        List<Geo> points=new ArrayList<>();for (int i=first;i<=last;i++) points.add(pointAt.apply(i));
        List<Decision> decisions=new ArrayList<>();
        for (int i=maneuver;i<decisionCount;i++) {
            Decision decision=decisionAt.apply(i);
            if (decision.routeIndex>last) break;
            if (decisions.size()>=2000) throw new IllegalArgumentException("Decision window capacity");
            decisions.add(decision);
        }
        return new Route(points,decisions,first,pointCount-1);
    }
}
