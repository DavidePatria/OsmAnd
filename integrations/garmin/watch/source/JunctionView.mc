import Toybox.Graphics;
import Toybox.Lang;
import Toybox.System;
import Toybox.WatchUi;

//! T02 placeholder view: build identifier on a dark background.
//! Verifies simulator rendering and update-in-place deployment.
class JunctionView extends WatchUi.View {

    private var _loggedDraw as Boolean = false;

    function initialize() {
        View.initialize();
    }

    function onUpdate(dc as Dc) as Void {
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_BLACK);
        var y = dc.getHeight() / 2;
        dc.drawText(dc.getWidth() / 2, y - 30, Graphics.FONT_MEDIUM, "Junction", Graphics.TEXT_JUSTIFY_CENTER);
        dc.drawText(dc.getWidth() / 2, y + 20, Graphics.FONT_SMALL, "BUILD " + JUNCTION_BUILD_ID, Graphics.TEXT_JUSTIFY_CENTER);
        var echo = getApp().echo;
        var replyId = echo.getReplyId();
        dc.drawText(dc.getWidth() / 2, y + 70, Graphics.FONT_SMALL, "ECHO TEST " + replyId, Graphics.TEXT_JUSTIFY_CENTER);
        echo.didDrawReply(replyId);
        if (!_loggedDraw) {
            System.println("JUNCTION_FRAME build=" + JUNCTION_BUILD_ID + " width=" + dc.getWidth() + " height=" + dc.getHeight());
            _loggedDraw = true;
        }
    }
}
