import Toybox.Lang;
const REPLAY_MODE = false;
function createInput(app as JunctionApp) as InputAdapter { return new EchoInput(app.echo); }
class EchoInput extends InputAdapter {
    private var _echo as EchoClient;
    function initialize(echo as EchoClient) { InputAdapter.initialize(); _echo=echo; }
    function start() as Void { _echo.start(); }
    function stop() as Void { _echo.stop(); }
}
