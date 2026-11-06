import Toybox.Lang;
const REPLAY_MODE = false;
const NAVIGATION_MODE = true;
//! Same input initialization and renderer; no transport timer in this bounded test.
function createInput(app as JunctionApp) as InputAdapter { return new NavigationInput(app.nav,true); }
