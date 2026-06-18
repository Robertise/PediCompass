import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.agent.stage0_safety import PediatricEmergencyScreen

def test_stage0_emergency():
    screen = PediatricEmergencyScreen()
    # 2 week old fever -> emergency
    flag, age = screen.screen("my 2 week old has a fever of 38.5")
    assert flag is not None
    assert flag.detected is True
    assert age == 14

    # Blue lips -> emergency
    flag, age = screen.screen("my child has blue lips")
    assert flag is not None
    assert flag.triggered_pattern == "cyanosis"

def test_stage0_no_emergency():
    screen = PediatricEmergencyScreen()
    # 3 year old fever -> not emergency
    flag, age = screen.screen("my 3 year old has a fever")
    assert flag is None

    # False positive test: fit of crying
    flag, age = screen.screen("my toddler had a fit of crying when I left the room")
    assert flag is None

    # False positive test: limping
    flag, age = screen.screen("my child is limping after the fall at the playground")
    assert flag is None

    # False positive test: grunting while pooping
    flag, age = screen.screen("my baby keeps grunting while pooping")
    assert flag is None
