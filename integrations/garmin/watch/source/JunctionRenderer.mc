import Toybox.Graphics;
import Toybox.Lang;

//! Vector renderer: positive scene y is forward; screen y is inverted here only.
class JunctionRenderer {
    function initialize() {}
    function draw(dc as Dc, state as NavigationState, now as Number, paused as Boolean) as Void {
        dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.clear();
        dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
        dc.drawText(dc.getWidth()/2,22,Graphics.FONT_XTINY,paused?"TEST REPLAY - PAUSED":"TEST REPLAY",Graphics.TEXT_JUSTIFY_CENTER);
        var status=state.status(now), scene=state.scene();
        if (!status.equals("active") || scene==null || scene["geometryMode"].equals("unavailable")) {
            var label="NO ROUTE";
            if (status.equals("recalculating")) { label="REROUTING"; }
            else if (status.equals("stale_transport")) { label="DATA EXPIRED"; }
            else if (status.equals("stale_source")) { label="POSITION OLD"; }
            else if (status.equals("active")) { label="DETAIL LIMITED"; }
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,195,Graphics.FONT_MEDIUM,label,Graphics.TEXT_JUSTIFY_CENTER);
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,365,Graphics.FONT_XTINY,"Recorded test input",Graphics.TEXT_JUSTIFY_CENTER);
            return;
        }
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
        dc.drawText(dc.getWidth()/2,53,Graphics.FONT_MEDIUM,state.displayDistance(now)+" m",Graphics.TEXT_JUSTIFY_CENTER);
        var cx=dc.getWidth()/2, cy=dc.getHeight()*0.54, scale=dc.getWidth()*0.33/scene["radiusDm"];
        var paths=scene["paths"], selected=null;
        dc.setClip(25,102,dc.getWidth()-50,270);
        dc.setColor(0x8193A6,Graphics.COLOR_BLACK);dc.setPenWidth(4);
        for (var i=0; i<paths.size(); i+=1) {
            if (paths[i]["role"].equals("selected")) { selected=paths[i]; }
            else { path(dc,paths[i]["points"],cx,cy,scale); }
        }
        if (selected!=null) {
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.setPenWidth(13);path(dc,selected["points"],cx,cy,scale);
            dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.setPenWidth(7);path(dc,selected["points"],cx,cy,scale);
        }
        dc.setPenWidth(2);
        var anchors=scene["anchors"];
        for (var i=0; i<anchors.size(); i+=1) {
            var p=anchors[i]["point"],x=cx+p[0]*scale,y=cy-p[1]*scale;
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.fillCircle(x,y,6);
            dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.drawCircle(x,y,6);
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_TRANSPARENT);
            dc.drawText(x+10,y-23,Graphics.FONT_XTINY,(i+1).toString(),Graphics.TEXT_JUSTIFY_LEFT);
        }
        dc.clearClip();dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
        var name=scene["roadName"];
        // Use the device font metrics, not a guessed character count, to fit a round display.
        while (name.length()>0 && dc.getTextWidthInPixels(name,Graphics.FONT_XTINY)>310) { name=name.substring(0,name.length()-1); }
        dc.drawText(dc.getWidth()/2,382,Graphics.FONT_XTINY,name,Graphics.TEXT_JUSTIFY_CENTER);
        dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
        var detail=scene["geometryMode"].equals("map_context")?"MOTOR ROADS":(scene["geometryMode"].equals("route_only")?"ROUTE ONLY":"PARTIAL ROADS");
        dc.drawText(dc.getWidth()/2,414,Graphics.FONT_XTINY,detail,Graphics.TEXT_JUSTIFY_CENTER);
    }
    private function path(dc as Dc, points as Array, cx as Numeric, cy as Numeric, scale as Numeric) as Void {
        for (var i=1; i<points.size(); i+=1) { dc.drawLine(cx+points[i-1][0]*scale,cy-points[i-1][1]*scale,cx+points[i][0]*scale,cy-points[i][1]*scale); }
    }
}
