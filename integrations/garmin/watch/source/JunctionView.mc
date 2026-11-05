import Toybox.Graphics;
import Toybox.Lang;
import Toybox.System;
import Toybox.WatchUi;

class JunctionView extends WatchUi.View {
    private var _loggedDraw as Boolean = false;
    private var _last as String = "";
    private var _renderer as JunctionRenderer = new JunctionRenderer();
    function initialize() { View.initialize(); }
    function onUpdate(dc as Dc) as Void {
        var app=getApp();
        if (REPLAY_MODE) {
            var now=app.input.now();
            _renderer.draw(dc,app.nav,now,app.input.paused());
            var status=app.nav.status(now), scene=app.nav.scene();
            var distance=app.nav.displayDistance(now);
            var key=status+":"+app.nav.sequence()+":"+distance;
            if (!_last.equals(key)) {
                _last=key;
                var visible=status.equals("active") && scene!=null && !scene["geometryMode"].equals("unavailable");
                System.println("JUNCTION_DRAW seq="+app.nav.sequence()+" state="+status+" mode="+(!visible?"unavailable":scene["geometryMode"])+
                    " paths="+(!visible?0:scene["paths"].size())+" anchors="+(!visible?0:scene["anchors"].size())+
                    " distance="+(distance==null?"unavailable":distance.toString())+" elapsedMs="+now);
            }
        } else {
            dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);dc.clear();
            dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
            dc.drawText(dc.getWidth()/2,190,Graphics.FONT_MEDIUM,"Junction",Graphics.TEXT_JUSTIFY_CENTER);
            dc.drawText(dc.getWidth()/2,240,Graphics.FONT_SMALL,"BUILD "+JUNCTION_BUILD_ID,Graphics.TEXT_JUSTIFY_CENTER);
            var replyId=app.echo.getReplyId();
            dc.drawText(dc.getWidth()/2,290,Graphics.FONT_SMALL,"ECHO TEST "+replyId,Graphics.TEXT_JUSTIFY_CENTER);
            app.echo.didDrawReply(replyId);
        }
        if (!_loggedDraw) {
            System.println("JUNCTION_FRAME build="+JUNCTION_BUILD_ID+" width="+dc.getWidth()+" height="+dc.getHeight());
            _loggedDraw=true;
        }
    }
}
