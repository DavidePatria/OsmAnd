import Toybox.WatchUi;
import Toybox.Lang;
class JunctionDelegate extends WatchUi.BehaviorDelegate {
    function initialize() { BehaviorDelegate.initialize(); }
    function onNextPage() as Boolean { getApp().input.advance(1);return true; }
    function onPreviousPage() as Boolean { getApp().input.advance(-1);return true; }
    function onSelect() as Boolean { getApp().input.togglePause();return true; }
}
