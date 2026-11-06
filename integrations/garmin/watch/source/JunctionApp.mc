import Toybox.Application;
import Toybox.Lang;
import Toybox.System;
import Toybox.WatchUi;

const JUNCTION_BUILD_ID = "T09-1";

//! Shared scene state and renderer, with build-selected replay or echo input.
class JunctionApp extends Application.AppBase {
    var echo as EchoClient = new EchoClient();
    var nav as NavigationState = new NavigationState();
    var input as InputAdapter;

    function initialize() {
        AppBase.initialize();
        input=createInput(self);
    }

    function onStart(state as Dictionary?) as Void {
        System.println("JUNCTION_START build=" + JUNCTION_BUILD_ID);
        input.start();
    }

    function onStop(state as Dictionary?) as Void {
        input.stop();
    }

    function getInitialView() as [Views] or [Views, InputDelegates] {
        return [ new JunctionView(), new JunctionDelegate() ];
    }
}

function getApp() as JunctionApp {
    return Application.getApp() as JunctionApp;
}
