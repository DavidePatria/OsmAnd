import Toybox.Application;
import Toybox.Lang;
import Toybox.System;
import Toybox.WatchUi;

const JUNCTION_BUILD_ID = "T03-3";

//! Minimal junction-companion scaffold (T02): shows a build identifier.
//! The real decoder/state/renderer replace this view in later tasks.
class JunctionApp extends Application.AppBase {
    var echo as EchoClient = new EchoClient();

    function initialize() {
        AppBase.initialize();
    }

    function onStart(state as Dictionary?) as Void {
        System.println("JUNCTION_START build=" + JUNCTION_BUILD_ID);
        echo.start();
    }

    function onStop(state as Dictionary?) as Void {
        echo.stop();
    }

    function getInitialView() as [Views] or [Views, InputDelegates] {
        return [ new JunctionView() ];
    }
}

function getApp() as JunctionApp {
    return Application.getApp() as JunctionApp;
}
