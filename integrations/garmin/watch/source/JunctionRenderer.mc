import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Math;

//! Vector renderer: positive scene y is forward; screen y is inverted here only.
class JunctionRenderer {
    function initialize() {}
    function draw(dc as Dc, state as NavigationState, now as Number, paused as Boolean) as Void {
        dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.clear();
        var heightScale=dc.getHeight()/454.0, widthScale=dc.getWidth()/454.0;
        if (REPLAY_MODE) {
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,22,Graphics.FONT_XTINY,paused?"TEST REPLAY - PAUSED":"TEST REPLAY",Graphics.TEXT_JUSTIFY_CENTER);
        }
        var status=state.status(now), scene=state.scene();
        if(status.equals("arrived")) {
            dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.setPenWidth(3);
            dc.drawCircle(dc.getWidth()/2,205*heightScale,108*(heightScale<widthScale?heightScale:widthScale));
            flag(dc,dc.getWidth()/2-38*widthScale,265*heightScale,16);
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,326*heightScale,Graphics.FONT_MEDIUM,"ARRIVED",Graphics.TEXT_JUSTIFY_CENTER);
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,380*heightScale,Graphics.FONT_XTINY,"Destination reached",Graphics.TEXT_JUSTIFY_CENTER);
            return;
        }
        if (!status.equals("active") || scene==null || scene["geometryMode"].equals("unavailable")) {
            var label="NO ROUTE";
            if (status.equals("recalculating")) { label="REROUTING"; }
            else if (status.equals("stale_transport")) { label="DATA EXPIRED"; }
            else if (status.equals("stale_source")) { label="POSITION OLD"; }
            else if (status.equals("active")) {
                label=scene!=null && scene["reason"].equals("geometry pending")?"LOADING JUNCTION":"DETAIL LIMITED";
            }
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,195*heightScale,Graphics.FONT_MEDIUM,label,Graphics.TEXT_JUSTIFY_CENTER);
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            var explanation=REPLAY_MODE?"Recorded test input":(label.equals("LOADING JUNCTION")?"Preparing road detail":"Waiting for phone");
            dc.drawText(dc.getWidth()/2,365*heightScale,Graphics.FONT_XTINY,explanation,Graphics.TEXT_JUSTIFY_CENTER);
            return;
        }
        var cx=dc.getWidth()/2, cy=dc.getHeight()/2, extent=dc.getWidth()<dc.getHeight()?dc.getWidth():dc.getHeight();
        var scale=extent*0.50/scene["radiusDm"];
        var paths=scene["paths"], selected=null;
        if (scene["geometryMode"].equals("layer_context")) {
            layeredPaths(dc,paths,cx,cy,scale);
        } else {
        dc.setColor(0x8193A6,Graphics.COLOR_BLACK);dc.setPenWidth(8);
        for (var i=0; i<paths.size(); i+=1) {
            if (paths[i]["role"].equals("selected")) { selected=paths[i]; }
            else { path(dc,paths[i]["points"],cx,cy,scale); }
        }
        if (selected!=null) {
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.setPenWidth(26);path(dc,selected["points"],cx,cy,scale);
            dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.setPenWidth(14);path(dc,selected["points"],cx,cy,scale);
            arrows(dc,selected,cx,cy,scale,null);
        }
        }
        dc.setPenWidth(2);
        var anchors=scene["anchors"], numberFont=junctionNumberFont(dc), labels=[];
        var top=(REPLAY_MODE?53:25)*heightScale+dc.getFontHeight(Graphics.FONT_MEDIUM)+3;
        var bottom=382*heightScale-3;
        for (var i=0; i<anchors.size(); i+=1) {
            var p=anchors[i]["point"],x=cx+p[0]*scale,y=cy-p[1]*scale;
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.fillCircle(x,y,6);
            dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.drawCircle(x,y,6);
        }
        // Place labels after all markers so their white text stays legible.
        for (var i=0; i<anchors.size(); i+=1) {
            var p=anchors[i]["point"],x=cx+p[0]*scale,y=cy-p[1]*scale,number=(i+1).toString();
            // Prefer the side facing away from the nearest other junction,
            // avoiding a visually reversed pair when anchors are close.
            var awayX=0,awayY=0,nearest=-1.0;
            for (var j=0;j<anchors.size();j+=1) {
                if (j==i) {continue;}
                var other=anchors[j]["point"],ox=(p[0]-other[0])*scale,oy=-(p[1]-other[1])*scale,dist=ox*ox+oy*oy;
                if (nearest<0 || dist<nearest) {
                    nearest=dist;awayX=0;awayY=0;
                    if (Math.abs(ox)>=Math.abs(oy) && ox!=0) {awayX=ox<0?-1:1;}
                    else if (oy!=0) {awayY=oy<0?-1:1;}
                }
            }
            var font=numberFont,box=JunctionLabelLayout.chooseAway(x,y,dc.getTextWidthInPixels(number,font),dc.getFontHeight(font),dc.getWidth(),dc.getHeight(),top,bottom,labels,awayX,awayY);
            // Keep every junction numbered, reducing font size only if the
            // largest choice cannot fit on the available round surface.
            if (box==null) {
                var smaller=[Graphics.FONT_MEDIUM,Graphics.FONT_SMALL,Graphics.FONT_TINY,Graphics.FONT_XTINY];
                for (var j=0;j<smaller.size() && box==null;j+=1) {
                    if (dc.getFontHeight(smaller[j])>=dc.getFontHeight(font)) {continue;}
                    var candidate=JunctionLabelLayout.chooseAway(x,y,dc.getTextWidthInPixels(number,smaller[j]),dc.getFontHeight(smaller[j]),dc.getWidth(),dc.getHeight(),top,bottom,labels,awayX,awayY);
                    if (candidate!=null) {font=smaller[j];box=candidate;}
                }
            }
            if (box==null) {box=[x+10,y-dc.getFontHeight(font)-3,dc.getTextWidthInPixels(number,font),dc.getFontHeight(font)];}
            labels.add(box);
            labelLeader(dc,x,y,box);
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_TRANSPARENT);
            dc.drawText(box[0],box[1],font,number,Graphics.TEXT_JUSTIFY_LEFT);
        }
        if(scene.hasKey("destination")) {
            var end=scene["destination"];
            flag(dc,cx+end[0]*scale,cy-end[1]*scale,5);
        }
        if (REPLAY_MODE) {
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,22,Graphics.FONT_XTINY,paused?"TEST REPLAY - PAUSED":"TEST REPLAY",Graphics.TEXT_JUSTIFY_CENTER);
        }
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
        dc.drawText(dc.getWidth()/2,(REPLAY_MODE?53:25)*heightScale,Graphics.FONT_MEDIUM,state.displayDistance(now)+" m",Graphics.TEXT_JUSTIFY_CENTER);
        var name=scene["roadName"];
        // Use the device font metrics, not a guessed character count, to fit a round display.
        while (name.length()>0 && dc.getTextWidthInPixels(name,Graphics.FONT_XTINY)>310*widthScale) { name=name.substring(0,name.length()-1); }
        dc.drawText(dc.getWidth()/2,382*heightScale,Graphics.FONT_XTINY,name,Graphics.TEXT_JUSTIFY_CENTER);
        if (!scene["geometryMode"].equals("map_context") && !scene["geometryMode"].equals("layer_context")) {
            dc.setColor(0x8CA5BF,Graphics.COLOR_BLACK);
            var detail=scene["geometryMode"].equals("route_only")?"ROUTE ONLY":"PARTIAL ROADS";
            dc.drawText(dc.getWidth()/2,414*heightScale,Graphics.FONT_XTINY,detail,Graphics.TEXT_JUSTIFY_CENTER);
        }
    }
    //! Pole foot is the actual destination; checkerboard extends above/right.
    private function flag(dc as Dc,x as Numeric,y as Numeric,cell as Number) as Void {
        dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.setPenWidth(3);
        dc.drawLine(x,y,x,y-cell*6);
        dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);
        dc.fillRectangle(x+1,y-cell*6-1,cell*4+2,cell*3+2);
        for(var row=0;row<3;row+=1) {
            for(var col=0;col<4;col+=1) {
                dc.setColor((row+col)%2==0?Graphics.COLOR_WHITE:0x343A43,Graphics.COLOR_BLACK);
                dc.fillRectangle(x+2+col*cell,y-cell*6+row*cell,cell,cell);
            }
        }
    }
    private function path(dc as Dc, points as Array, cx as Numeric, cy as Numeric, scale as Numeric) as Void {
        for (var i=1; i<points.size(); i+=1) { dc.drawLine(cx+points[i-1][0]*scale,cy-points[i-1][1]*scale,cx+points[i][0]*scale,cy-points[i][1]*scale); }
    }
    //! Thin white line associates a displaced label with its junction marker.
    private function labelLeader(dc as Dc,x as Numeric,y as Numeric,box as Array) as Void {
        var endX=x<box[0]?box[0]:(x>box[0]+box[2]?box[0]+box[2]:x);
        var endY=y<box[1]?box[1]:(y>box[1]+box[3]?box[1]+box[3]:y);
        var dx=endX-x,dy=endY-y,length=Math.sqrt(dx*dx+dy*dy);
        if (length<=8) {return;}
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_TRANSPARENT);dc.setPenWidth(1);
        dc.drawLine(x+dx*8/length,y+dy*8/length,endX,endY);
    }
    //! Pick the device font closest to twice the former junction-label height.
    private function junctionNumberFont(dc as Dc) as Graphics.FontType {
        var target=dc.getFontHeight(Graphics.FONT_XTINY)*2;
        var fonts=[Graphics.FONT_TINY,Graphics.FONT_SMALL,Graphics.FONT_MEDIUM,Graphics.FONT_LARGE];
        var best=fonts[0],difference=Math.abs(dc.getFontHeight(best)-target);
        for (var i=1;i<fonts.size();i+=1) {
            var candidate=Math.abs(dc.getFontHeight(fonts[i])-target);
            if (candidate<difference) {best=fonts[i];difference=candidate;}
        }
        return best;
    }
    //! Screen-space chevrons follow the selected path's ordered points. For
    //! layered scenes draw each chevron with its road level, below higher roads.
    private function arrows(dc as Dc,p as Dictionary,cx as Numeric,cy as Numeric,scale as Numeric,level as Number?) as Void {
        var points=p["points"],remaining=24.0;
        dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.setPenWidth(3);
        for (var i=1;i<points.size();i+=1) {
            if (level!=null && p["segmentLayers"][i-1]!=level) {remaining=24.0;continue;}
            var x=cx+points[i-1][0]*scale,y=cy-points[i-1][1]*scale;
            var dx=(points[i][0]-points[i-1][0])*scale,dy=-(points[i][1]-points[i-1][1])*scale;
            var length=Math.sqrt(dx*dx+dy*dy);
            if (length<=0) {continue;}
            var ux=dx/length,uy=dy/length;
            while (remaining<=length) {
                var tx=x+ux*remaining,ty=y+uy*remaining;
                dc.drawLine(tx,ty,tx-ux*8-uy*4,ty-uy*8+ux*4);
                dc.drawLine(tx,ty,tx-ux*8+uy*4,ty-uy*8-ux*4);
                remaining+=76;
            }
            remaining-=length;
        }
    }
    //! Lower roads first. Black casing separates a bridge from roads below it;
    //! connected alternatives remain gray, and only the selected route is yellow.
    private function layeredPaths(dc as Dc,paths as Array,cx as Numeric,cy as Numeric,scale as Numeric) as Void {
        var low=10,high=-10,selected=null;
        for (var i=0;i<paths.size();i+=1) {
            var p=paths[i];
            if (p["role"].equals("selected")) {
                selected=p;
                for (var j=0;j<p["segmentLayers"].size();j+=1) { low=p["segmentLayers"][j]<low?p["segmentLayers"][j]:low;high=p["segmentLayers"][j]>high?p["segmentLayers"][j]:high; }
            } else { low=p["layer"]<low?p["layer"]:low;high=p["layer"]>high?p["layer"]:high; }
        }
        for (var level=low;level<=high;level+=1) {
            if (level>low) {
                dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.setPenWidth(20);
                for (var i=0;i<paths.size();i+=1) { if (!paths[i]["role"].equals("selected") && paths[i]["layer"]==level) { path(dc,paths[i]["points"],cx,cy,scale); } }
            }
            dc.setColor(0x8193A6,Graphics.COLOR_BLACK);dc.setPenWidth(8);
            for (var i=0;i<paths.size();i+=1) { if (!paths[i]["role"].equals("selected") && paths[i]["layer"]==level) { path(dc,paths[i]["points"],cx,cy,scale); } }
            if (selected!=null) {
                dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.setPenWidth(26);selectedLevel(dc,selected,level,cx,cy,scale);
                dc.setColor(0xFFD166,Graphics.COLOR_BLACK);dc.setPenWidth(14);selectedLevel(dc,selected,level,cx,cy,scale);
                arrows(dc,selected,cx,cy,scale,level);
            }
        }
    }
    private function selectedLevel(dc as Dc,p as Dictionary,level as Number,cx as Numeric,cy as Numeric,scale as Numeric) as Void {
        for (var i=0;i<p["segmentLayers"].size();i+=1) {
            if (p["segmentLayers"][i]==level) { path(dc,[p["points"][i],p["points"][i+1]],cx,cy,scale); }
        }
    }
}

//! Bounded layout for up to four labels on a round watch face.
module JunctionLabelLayout {
    function fits(x as Numeric,y as Numeric,w as Numeric,h as Numeric,width as Number,height as Number,top as Numeric,bottom as Numeric,placed as Array) as Boolean {
        if (x<0 || y<top || x+w>width || y+h>bottom) {return false;}
        var cx=width/2.0,cy=height/2.0,r=(width<height?width:height)/2.0-3;
        for (var i=0;i<4;i+=1) {
            var px=(i%2==0?x:x+w)-cx,py=(i<2?y:y+h)-cy;
            if (px*px+py*py>r*r) {return false;}
        }
        for (var i=0;i<placed.size();i+=1) {
            var b=placed[i];
            if (x<b[0]+b[2]+4 && x+w+4>b[0] && y<b[1]+b[3]+4 && y+h+4>b[1]) {return false;}
        }
        return true;
    }
    function choose(ax as Numeric,ay as Numeric,w as Number,h as Number,width as Number,height as Number,top as Numeric,bottom as Numeric,placed as Array) as Array? {
        return chooseAway(ax,ay,w,h,width,height,top,bottom,placed,0,0);
    }
    function chooseAway(ax as Numeric,ay as Numeric,w as Number,h as Number,width as Number,height as Number,top as Numeric,bottom as Numeric,placed as Array,awayX as Number,awayY as Number) as Array? {
        var dx=[1,-1,1,-1,0,0,1,-1],dy=[-1,-1,0,0,-1,1,1,1];
        for (var ring=0;ring<10;ring+=1) {
            var gap=10+ring*20;
            for (var pass=0;pass<2;pass+=1) {
                for (var i=0;i<dx.size();i+=1) {
                    var preferred=(awayX!=0 && dx[i]==awayX) || (awayY!=0 && dy[i]==awayY) || (awayX==0 && awayY==0);
                    if ((pass==0 && !preferred) || (pass==1 && preferred)) {continue;}
                    var x=dx[i]>0?ax+gap:(dx[i]<0?ax-gap-w:ax-w/2.0);
                    var y=dy[i]>0?ay+gap:(dy[i]<0?ay-gap-h:ay-h/2.0);
                    if (fits(x,y,w,h,width,height,top,bottom,placed)) {return [x,y,w,h];}
                }
            }
        }
        return null;
    }
}
