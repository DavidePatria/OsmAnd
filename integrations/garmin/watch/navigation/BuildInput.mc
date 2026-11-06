import Toybox.Lang;
const REPLAY_MODE = false;
const NAVIGATION_MODE = true;
function createInput(app as JunctionApp) as InputAdapter { return new NavigationInput(app.nav,false); }
