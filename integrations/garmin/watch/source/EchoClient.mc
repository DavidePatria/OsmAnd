import Toybox.Communications;
import Toybox.Lang;
import Toybox.System;
import Toybox.Timer;
import Toybox.Time;
import Toybox.WatchUi;

//! T03 bounded transport probe. This is not the v1 navigation protocol.
class EchoClient {
    private var _timer as Timer.Timer = new Timer.Timer();
    private var _epoch as String = "";
    private var _nextId as Number = 0;
    private var _pendingId as Number = 0;
    private var _sentAt as Number = 0;
    private var _displayedId as Number = 0;
    private var _replyId as Number = 0;
    private var _sendBusy as Boolean = false;
    private var _ticks as Number = 0;

    function start() as Void {
        _epoch = Time.now().value().toString() + ":" + System.getTimer();
        Communications.registerForPhoneAppMessages(method(:onPhone));
        _timer.start(method(:tick), 1000, true);
    }

    function stop() as Void {
        _timer.stop();
        Communications.registerForPhoneAppMessages(null);
    }

    function tick() as Void {
        _ticks += 1;
        // Six displayed replies let request 6 acknowledge display 5 on the phone.
        // Exit through the SDK so monkeydo can finish without forced disconnects.
        if (_displayedId >= 6 || _ticks > 35) {
            System.println("JUNCTION_ECHO_DONE displayed=" + _displayedId);
            System.exit();
            return;
        }
        // One outstanding request; no packet history or catch-up queue.
        var now = System.getTimer();
        if (_pendingId != 0) {
            if (now >= _sentAt && now - _sentAt < 3000) { return; }
            System.println("JUNCTION_ECHO_TIMEOUT id=" + _pendingId);
            _pendingId = 0;
        }
        if (_sendBusy) { return; }
        // Bound unattended probe traffic. Re-launch to start a fresh experiment.
        if (_nextId >= 30) { _timer.stop(); return; }
        _nextId += 1;
        _pendingId = _nextId;
        _sentAt = now;
        _sendBusy = true;
        System.println("JUNCTION_ECHO_REQUEST epoch=" + _epoch + " id=" + _pendingId + " displayed=" + _displayedId);
        try {
            Communications.transmit({
                "kind" => "echo_request", "epoch" => _epoch,
                "requestId" => _pendingId, "displayedId" => _displayedId
            }, null, new EchoSendListener(self));
        } catch (error) {
            _sendBusy = false;
            _pendingId = 0;
            System.println("JUNCTION_ECHO_SEND_EXCEPTION");
        }
    }

    function sendFinished(success as Boolean) as Void {
        _sendBusy = false;
        if (!success) {
            _pendingId = 0;
            System.println("JUNCTION_ECHO_SEND_ERROR");
        }
    }

    function onPhone(message as Communications.PhoneAppMessage) as Void {
        var data = message.data;
        if (!(data instanceof Dictionary)) { return; }
        var now = System.getTimer();
        var kind = data["kind"];
        var epoch = data["epoch"];
        System.println("JUNCTION_ECHO_RX kind=" + kind + " epoch=" + epoch + " id=" + data["requestId"] + " pending=" + _pendingId + " age=" + (now - _sentAt));
        if (!(kind instanceof String) || !(epoch instanceof String) ||
            !kind.equals("echo_reply") || !epoch.equals(_epoch) ||
            _pendingId == 0 || data["requestId"] != _pendingId ||
            now < _sentAt || now - _sentAt >= 3000) {
            System.println("JUNCTION_ECHO_REJECT");
            return;
        }
        _replyId = _pendingId;
        _pendingId = 0;
        System.println("JUNCTION_ECHO_REPLY id=" + _replyId);
        WatchUi.requestUpdate();
    }

    function getReplyId() as Number { return _replyId; }

    function didDrawReply(id as Number) as Void {
        if (id > _displayedId) {
            _displayedId = id;
            System.println("JUNCTION_ECHO_DISPLAY id=" + id);
        }
    }
}

class EchoSendListener extends Communications.ConnectionListener {
    private var _client as EchoClient;
    function initialize(client as EchoClient) {
        ConnectionListener.initialize();
        _client = client;
    }
    function onComplete() as Void { _client.sendFinished(true); }
    function onError() as Void { _client.sendFinished(false); }
}
