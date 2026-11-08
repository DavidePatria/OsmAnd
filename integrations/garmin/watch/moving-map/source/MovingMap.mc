import Toybox.Application;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.Position;
import Toybox.System;
import Toybox.WatchUi;

//! Isolated map experiment. The sample line is synthetic, not directions.
class MovingMapApp extends Application.AppBase {
    private var _positionLogged as Boolean = false;
    function initialize() { AppBase.initialize(); }
    function onStart(state as Dictionary?) as Void {
        System.println("MOVING_MAP_START");
        Position.enableLocationEvents(Position.LOCATION_CONTINUOUS, method(:onPosition));
    }
    function onStop(state as Dictionary?) as Void {
        Position.enableLocationEvents(Position.LOCATION_DISABLE, null);
    }
    function onPosition(info as Position.Info) as Void {
        if (!_positionLogged && info != null && info.position != null) {
            _positionLogged = true;
            System.println("MOVING_MAP_POSITION_AVAILABLE");
        }
    }
    function getInitialView() as [Views] or [Views, InputDelegates] { return [new MovingMapView()]; }
}

class MovingMapView extends WatchUi.MapTrackView {
    private var _logged as Boolean = false;
    function initialize() {
        System.println("MOVING_MAP_INIT");
        MapTrackView.initialize();
        System.println("MOVING_MAP_NATIVE_INIT");
        setMapMode(WatchUi.MAP_MODE_PREVIEW);
        // This short public test fixture is an invented line, not a routed path.
        var path = new WatchUi.MapPolyline();
        path.setColor(Graphics.COLOR_YELLOW);
        path.setWidth(5);
        path.addLocation(point(41.8820,12.5130));
        path.addLocation(point(41.8815,12.5133));
        path.addLocation(point(41.8810,12.5138));
        path.addLocation(point(41.8805,12.5142));
        path.addLocation(point(41.8800,12.5146));
        System.println("MOVING_MAP_PATH_READY");
        setPolyline(path);
        System.println("MOVING_MAP_PATH_SET");
        setMapVisibleArea(point(41.8830,12.5115),point(41.8790,12.5160));
        var settings = System.getDeviceSettings();
        setScreenVisibleArea(0,0,settings.screenWidth,settings.screenHeight);
        System.println("MOVING_MAP_AREA_SET");
    }
    private function point(lat as Float, lon as Float) as Position.Location {
        return new Position.Location({:latitude=>lat,:longitude=>lon,:format=>:degrees});
    }
    function onUpdate(dc as Dc) as Void {
        if (!_logged) { System.println("MOVING_MAP_DRAW_START"); }
        MapView.onUpdate(dc);
        dc.setColor(Graphics.COLOR_BLACK,Graphics.COLOR_BLACK);
        dc.fillRectangle(0,0,dc.getWidth(),35);
        dc.setColor(Graphics.COLOR_WHITE,Graphics.COLOR_BLACK);
        dc.drawText(dc.getWidth()/2,7,Graphics.FONT_XTINY,"DEMO ROUTE",Graphics.TEXT_JUSTIFY_CENTER);
        if (!_logged) {
            _logged = true;
            System.println("MOVING_MAP_FRAME width="+dc.getWidth()+" height="+dc.getHeight());
        }
    }
}
