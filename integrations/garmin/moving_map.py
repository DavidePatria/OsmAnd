"""Build and exercise the separate Garmin moving-map prototype."""

import json
import os
import signal
import subprocess
import time

from replay import ensure_simulator


def run(dev, cfg, out, timeout, hold):
    out.mkdir(parents=True, exist_ok=True)
    report = {"status": "fail", "scope": "simulator drawing callback only; pixels and GPS movement unverified"}
    client = None
    log_path = out / "runtime.log"
    try:
        if dev.build_watch(cfg, out / "build", jungle=dev.TOOL_DIR / "watch/moving-map/monkey.jungle"):
            raise RuntimeError("prototype build failed")
        sdk, env, simulator = ensure_simulator(cfg, out)
        report.update(simulator)
        with log_path.open("wb") as log:
            client = subprocess.Popen([str(sdk / "bin/monkeydo"), str(out / "build/Junction.prg"), "fr970"],
                                      stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                text = log_path.read_text(errors="replace")
                if "MOVING_MAP_FRAME width=454 height=454" in text:
                    report["status"] = "pass"
                    break
                if client.poll() is not None:
                    raise RuntimeError("prototype exited before drawing; see runtime.log")
                time.sleep(0.2)
            if report["status"] != "pass":
                raise RuntimeError("timed out waiting for drawing callback")
            dev.log("Moving map drew a frame in the simulator. Visual map and movement still need review.")
            if hold:
                dev.log("Leave this running while reviewing; press Ctrl+C to stop the demo.")
                try:
                    client.wait()
                except KeyboardInterrupt:
                    pass
                if client.poll() not in (None, 0):
                    report.update(status="fail", reason="prototype exited during review; see runtime.log")
    except (OSError, RuntimeError) as error:
        report.update(status="fail", reason=str(error))
    finally:
        if client is not None and client.poll() is None:
            try:
                os.killpg(client.pid, signal.SIGTERM)
                client.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(client.pid, signal.SIGKILL)
                client.wait()
        (out / "smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    dev.log("moving-map check: " + report["status"] + "; evidence: " + str(out))
    return 0 if report["status"] == "pass" else 1
